"""The `shorten-me` command line: run the service, or delete expired links."""

import argparse
from collections.abc import Sequence
from datetime import timedelta

import uvicorn

from shorten_me.app import create_app, utc_now
from shorten_me.schema import (
    DatabaseNotFound,
    create_db_engine,
    require_database,
    upgrade_to_head,
)
from shorten_me.service import InvalidGracePeriod, open_service
from shorten_me.settings import Settings


def main(argv: Sequence[str] | None = None) -> None:
    """Run the service, or the given command, with settings from the environment."""
    parser = argparse.ArgumentParser(
        prog="shorten-me", description="A small URL shortener. Without a command, run the service."
    )
    commands = parser.add_subparsers(title="commands", dest="command")
    cleanup_parser = commands.add_parser("cleanup", help="delete links that expired long ago")
    cleanup_parser.add_argument(
        "--grace-days",
        dest="grace",
        metavar="DAYS",
        type=_days,
        default=timedelta(days=30),
        help="keep links for this many days after they expire (default: 30)",
    )
    args = parser.parse_args(argv)
    settings = Settings()
    if args.command == "cleanup":
        cleanup(settings, args.grace)
    else:
        serve(settings)


def cleanup(settings: Settings, grace: timedelta) -> None:
    """Delete links whose expiry passed more than `grace` ago, and print how many."""
    try:
        deleted = _delete_expired(settings.database_url, grace)
    except (DatabaseNotFound, InvalidGracePeriod) as error:
        raise SystemExit(f"shorten-me cleanup: {error}") from error
    print(f"Expired links deleted: {deleted}")


def serve(settings: Settings) -> None:
    """Run the web service."""
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        proxy_headers=settings.proxy_headers,
        forwarded_allow_ips=settings.forwarded_allow_ips,
    )


def _days(text: str) -> timedelta:
    try:
        return timedelta(days=int(text))
    except (ValueError, OverflowError) as error:
        raise argparse.ArgumentTypeError(f"invalid number of days: {text!r}") from error


def _delete_expired(database_url: str, grace: timedelta) -> int:
    require_database(database_url)
    upgrade_to_head(database_url)
    engine = create_db_engine(database_url)
    try:
        with open_service(engine, utc_now) as service:
            return service.delete_expired(grace)
    finally:
        engine.dispose()
