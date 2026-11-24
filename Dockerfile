FROM python:3.15-slim@sha256:1c670c3568107e243bfd05457ad9ca0b11c35a855c985af73e4452db9a714e70 AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.7@sha256:96f40d3904aad8d0bd010539001d36c8e2188b981e1334471a90c4a1d93bb490 /uv /uvx /bin/

ENV UV_PYTHON_DOWNLOADS=0 \
    UV_NO_DEV=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

FROM python:3.15-slim@sha256:1c670c3568107e243bfd05457ad9ca0b11c35a855c985af73e4452db9a714e70

RUN useradd --system --no-create-home app \
    && mkdir /data \
    && chown app /data

COPY --from=builder /app/.venv /app/.venv

ENV PATH=/app/.venv/bin:$PATH \
    SHORTEN_ME_HOST=0.0.0.0 \
    SHORTEN_ME_DATABASE_URL=sqlite:////data/shorten_me.db

VOLUME /data
USER app
EXPOSE 8000
CMD ["shorten-me"]
