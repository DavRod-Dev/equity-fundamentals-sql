"""``python -m efs <command>``."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb

from efs import config, fetch, load, runner


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="efs", description="analytical SQL over SEC Financial Statement Data Sets")
    p.add_argument("--db", default=None, help=f"DuckDB file (default: {config.DEFAULT_DB_PATH})")
    sub = p.add_subparsers(dest="command", required=True)

    ld = sub.add_parser("load", help="fetch configured quarters and load the raw tables")
    ld.add_argument("--force", action="store_true", help="re-download archives even if cached")
    ld.add_argument("--quarters", nargs="*", help="override config/quarters.json")

    sub.add_parser("build", help="create core views and tables from sql/models")
    sub.add_parser("test", help="run tests/quality/*.sql")
    sub.add_parser("list", help="list queries in sql/queries")

    q = sub.add_parser("query", help="run one query from sql/queries and print a Markdown table")
    q.add_argument("name")
    q.add_argument("--limit", type=int, default=25)
    q.add_argument("--all", action="store_true", help="no row limit")
    return p


def _load(con: duckdb.DuckDBPyConnection, args: argparse.Namespace) -> None:
    quarters = tuple(args.quarters) if args.quarters else config.load_quarters()
    fetcher = fetch.Fetcher(user_agent=config.user_agent())
    load.ensure_raw_schema(con)
    for quarter in quarters:
        archive = fetcher.fetch(quarter, force=args.force)
        files = load.extract(archive)
        load.load_quarter(con, quarter, files)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    path = Path(args.db) if args.db else config.db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        con = duckdb.connect(str(path))
        try:
            if args.command == "load":
                _load(con, args)
            elif args.command == "build":
                runner.build(con)
            elif args.command == "test":
                return 0 if all(r.passed for r in runner.quality(con)) else 1
            elif args.command == "list":
                for q in runner.discover_queries():
                    print(f"{q.name:<34} {q.purpose}")
            elif args.command == "query":
                cols, rows = runner.run_query(con, args.name, limit=None if args.all else args.limit)
                print(runner.markdown_table(cols, rows))
        finally:
            con.close()
    except (config.ConfigError, fetch.FetchError, load.SchemaError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
