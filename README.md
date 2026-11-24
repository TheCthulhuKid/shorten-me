# shorten-me

A small URL shortener: post a long URL, get a short code, and the code redirects back.

## Running

Requires [uv](https://docs.astral.sh/uv/) 0.13.7 or later in the 0.13 series (`required-version`
in `pyproject.toml`; CI installs the newest version in that range).

```sh
uv sync
uv run shorten-me
```

The service listens on `http://127.0.0.1:8000`. Open it in a browser for a form that shortens
links (it needs JavaScript); interactive API docs are at `/docs`.
Settings come from environment variables:

| Variable | Default |
|---|---|
| `SHORTEN_ME_DATABASE_URL` | `sqlite:///shorten_me.db` |
| `SHORTEN_ME_HOST` | `127.0.0.1` |
| `SHORTEN_ME_PORT` | `8000` |
| `SHORTEN_ME_PUBLIC_URL` | unset (the address clients reach the service at, such as `https://sho.rt`) |
| `SHORTEN_ME_RATE_LIMIT` | `10` (links per client per minute; `0` turns it off) |
| `SHORTEN_ME_PROXY_HEADERS` | `true` |
| `SHORTEN_ME_FORWARDED_ALLOW_IPS` | `127.0.0.1,::1` |

Database migrations are applied on startup.

### Deleting expired links

```sh
uv run shorten-me cleanup               # links that expired more than 30 days ago
uv run shorten-me cleanup --grace-days 7
```

Expired links answer 410 until they are deleted, then 404, and their aliases can be claimed
again. Run the command on a schedule (cron, a systemd timer, or
`docker run -v shorten-me-data:/data shorten-me shorten-me cleanup`); the service never
deletes links by itself. Deleted links' codes are never handed out again.

The command exits with an error if the SQLite file in `SHORTEN_ME_DATABASE_URL` doesn't
exist. The default URL is relative to the working directory, so give cron an absolute path.

### Behind a reverse proxy

Set `SHORTEN_ME_PUBLIC_URL` to the address clients use. `short_url` is then built from it,
whatever `Host` header a request carries, and links that point back at the service are
refused. Without it, `short_url` follows the request's `Host` header and scheme.

With `SHORTEN_ME_PROXY_HEADERS` on, the service takes the client address and scheme from
`X-Forwarded-For` and `X-Forwarded-Proto`, but only from the addresses in
`SHORTEN_ME_FORWARDED_ALLOW_IPS` (comma-separated IPs or networks, or `*` for any). The rate
limit depends on this, and so does `short_url` when `SHORTEN_ME_PUBLIC_URL` is unset: its
scheme comes from `X-Forwarded-Proto` and its host from the `Host` header, which the proxy
must then pass through (in nginx, `proxy_set_header Host $host`).
A proxy outside the container, as with Docker, isn't on `127.0.0.1`, so set
`SHORTEN_ME_FORWARDED_ALLOW_IPS` to its address.

### Docker

```sh
docker build -t shorten-me .
docker run -p 8000:8000 -v shorten-me-data:/data shorten-me
```

In the image the service listens on `0.0.0.0:8000` and keeps its SQLite database in the
`/data` volume.

## API

* `GET /` returns the HTML form. It posts to `POST /` and converts the expiry from the
  browser's local time to UTC. The page is served with a Content-Security-Policy that only
  allows its own inline script and stylesheet, so editing `static/index.html` needs no extra
  step: the hashes are computed when the service starts.
* `POST /` with a JSON body `{"long_url": "https://..."}` returns
  `{"code": ..., "short_url": ..., "expires_at": ...}`.
  Shortening the same URL again returns the same code. A URL returns 422 if it isn't
  http(s), is longer than 2048 characters, contains whitespace or control characters, carries a username or
  password, or points to `localhost` or a private, loopback or otherwise non-public IP
  address. Hostnames aren't looked up, so a name that resolves to a private address is
  accepted. With `SHORTEN_ME_PUBLIC_URL` set, a URL on the service's own address is refused
  too.
* `POST /` with `{"long_url": "https://...", "alias": "my-link"}` uses the alias as the code.
  A link keeps its generated code, and can have several aliases that share its hit count.
  Posting the same URL and alias again returns 200; an alias that belongs to another URL
  returns 409. Aliases are case-sensitive and have 3 to 32 letters, digits, `-` or `_`. An
  alias that could also be a generated code (see below) and the names `docs` and `redoc`
  return 422.
* `POST /` with `"expires_at": "2027-01-01T00:00:00Z"` makes the link expire then. The time
  needs a timezone and must be in the future, or the request returns 422. A link expires
  for all its codes and aliases. Posting the URL again only moves its expiry later, and
  posting without `expires_at` makes it permanent, so a request can't cut short a link that
  someone else holds; this also revives an expired link. `expires_at` in the response is the
  expiry that applies (`null` for never). All times in responses are in UTC and end in `Z`.
* `POST /` with a body over 25 KB returns 413.
* `POST /` is rate limited per client IP address (per /64 network for IPv6): a client can
  make `SHORTEN_ME_RATE_LIMIT` requests in a burst, and gets them back evenly over a minute.
  Beyond that it returns 429 with a `Retry-After` header in seconds. Redirects and stats
  aren't limited.
* `GET /{code}` redirects (307) to the long URL and counts a hit. Unknown codes return 404;
  expired links return 410. `HEAD /{code}` answers the same way without counting a hit.
* `GET /{code}/stats` returns the long URL, hit count, creation time and expiry (UTC)
  without counting a hit. It works for expired links too.

## How codes work

Each link's database id is written in a shuffled 56-character alphabet that leaves out
0, 1, I, l, o and O, so codes are short and hard to misread. Codes are sequential ids, so
they can be enumerated.

Every string made only of alphabet characters that doesn't start with `D` is some id's code,
so an alias needs a `-`, `_`, one of the left-out characters, or a leading `D`.

## Development

```sh
uv sync --locked --group dev
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
.venv/bin/python -m ruff format --check .
```

After changing `models.py`, generate a migration, review it, and commit it with the change:

```sh
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic revision --autogenerate -m "describe the change"
```

Both commands use the database in `SHORTEN_ME_DATABASE_URL`; autogenerate compares the models
against it, so it has to be at the latest revision first.

Migrations live in `src/shorten_me/migrations/versions/`. A test fails if they don't match
the models.

The `links` table uses SQLite's `AUTOINCREMENT`, so the short code of a deleted link is never
handed out again. Autogenerate can't see that option, and a batch migration that rebuilds
`links` drops it unless it passes `table_kwargs={"sqlite_autoincrement": True}` to
`batch_alter_table`. A test fails if a migration loses it.

The service enforces foreign keys on SQLite (`create_db_engine`), so deleting a link deletes
its aliases. Migrations run without that, because SQLite can't rebuild a table that other
rows reference while foreign keys are enforced.

`create_db_engine` also opens every SQLite transaction with `BEGIN IMMEDIATE`. Python's
`sqlite3` would otherwise commit a released savepoint that the request later rolls back, and a
transaction that reads and then writes could fail with "database is locked". The cost is that
requests run one at a time against the database, including read-only ones.

CI runs the same checks and builds the Docker image on every push to `master` and every
pull request.
