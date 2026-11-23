# shorten-me
Simple url shortener.

## Implementation
FastAPI serves the requests and SQLAlchemy stores the links. Each link's database id is
written in a 56-character alphabet (no 0, 1, I, l, o or O) to make its short code.

## Endpoints
* `POST /` with a JSON body `{"long_url": "https://..."}` returns `{"code": ..., "short_url": ...}`.
  Shortening the same URL again returns the same code. A URL that isn't http(s) or is longer
  than 2048 characters returns 422.
* `GET /{code}` redirects (307) to the long URL and counts a hit. Unknown codes return 404.
* `GET /{code}/stats` returns the long URL, hit count and creation time without counting a hit.
