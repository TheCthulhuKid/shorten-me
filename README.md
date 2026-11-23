# shorten-me

A small URL shortener: post a long URL, get a short code, and the code redirects back.

## Running

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run shorten-me
```

The service listens on `http://127.0.0.1:8000`; interactive API docs are at `/docs`.
Settings come from environment variables:

| Variable | Default |
|---|---|
| `SHORTEN_ME_DATABASE_URL` | `sqlite:///shorten_me.db` |
| `SHORTEN_ME_HOST` | `127.0.0.1` |
| `SHORTEN_ME_PORT` | `8000` |
| `SHORTEN_ME_DEBUG` | `false` |

Database migrations are applied on startup.

### Docker

```sh
docker build -t shorten-me .
docker run -p 8000:8000 -v shorten-me-data:/data shorten-me
```

In the image the service listens on `0.0.0.0:8000` and keeps its SQLite database in the
`/data` volume.

## API

* `POST /` with a JSON body `{"long_url": "https://..."}` returns `{"code": ..., "short_url": ...}`.
  Shortening the same URL again returns the same code. A URL that isn't http(s) or is longer
  than 2048 characters returns 422.
* `POST /` with `{"long_url": "https://...", "alias": "my-link"}` uses the alias as the code.
  A link keeps its generated code, and can have several aliases that share its hit count.
  Posting the same URL and alias again returns 200; an alias that belongs to another URL
  returns 409. Aliases are case-sensitive and have 3 to 32 letters, digits, `-` or `_`. An
  alias that could also be a generated code (see below) and the names `docs` and `redoc`
  return 422.
* `GET /{code}` redirects (307) to the long URL and counts a hit. Unknown codes return 404.
* `GET /{code}/stats` returns the long URL, hit count and creation time (UTC) without
  counting a hit.

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

CI runs the same checks and builds the Docker image on every push to `master` and every
pull request.
