"""Run SQL files: models, queries and quality assertions.

All three are plain ``.sql`` files; what differs is what the runner does
with the result.

models     sql/models/NN_<name>.sql   -> the file's first line says how to
                                         materialise it: ``-- view`` or
                                         ``-- table``; object is core.<name>
queries    sql/queries/<name>.sql     -> executed, rows returned
quality    tests/quality/<name>.sql   -> executed, any row is a failure
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import duckdb

from efs import config

_PREFIX = re.compile(r"^\d+_")
_MATERIALIZE = re.compile(r"^--\s*(view|table)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Model:
    name: str
    materialization: str
    path: Path

    @property
    def qualified_name(self) -> str:
        return f"core.{self.name}"


def _strip(sql: str) -> str:
    return sql.strip().rstrip(";").strip()


def discover_models(models_dir: Path = config.MODELS_DIR) -> list[Model]:
    models = []
    for path in sorted(models_dir.glob("*.sql")):
        first = path.read_text(encoding="utf-8").lstrip().splitlines()[0]
        m = _MATERIALIZE.match(first)
        if not m:
            raise ValueError(f"{path.name}: first line must be '-- view' or '-- table'")
        models.append(Model(_PREFIX.sub("", path.stem), m.group(1).lower(), path))
    return models


def build(con: duckdb.DuckDBPyConnection, models_dir: Path = config.MODELS_DIR, log=print) -> list[Model]:
    con.execute("CREATE SCHEMA IF NOT EXISTS core")
    models = discover_models(models_dir)
    for model in models:
        body = _strip(model.path.read_text(encoding="utf-8"))
        con.execute(f"CREATE OR REPLACE {model.materialization.upper()} {model.qualified_name} AS\n{body}")
        n = con.execute(f"SELECT count(*) FROM {model.qualified_name}").fetchone()[0]
        log(f"[build] {model.materialization:<5} {model.qualified_name:<32} {n:>12,} rows")
    return models


@dataclass(frozen=True)
class QueryInfo:
    name: str
    purpose: str
    path: Path


def discover_queries(queries_dir: Path = config.QUERIES_DIR) -> list[QueryInfo]:
    out = []
    for path in sorted(queries_dir.glob("*.sql")):
        first = path.read_text(encoding="utf-8").lstrip().splitlines()[0]
        purpose = first.lstrip("-").strip()
        out.append(QueryInfo(_PREFIX.sub("", path.stem), purpose, path))
    return out


def run_query(con: duckdb.DuckDBPyConnection, name: str, *, limit: int | None = None,
              queries_dir: Path = config.QUERIES_DIR) -> tuple[list[str], list[tuple]]:
    matches = [q for q in discover_queries(queries_dir) if q.name == name or q.path.stem == name]
    if not matches:
        raise FileNotFoundError(f"no query named {name!r} in {queries_dir}")
    sql = _strip(matches[0].path.read_text(encoding="utf-8"))
    if limit is not None:
        sql = f"SELECT * FROM (\n{sql}\n) AS q LIMIT {int(limit)}"
    cur = con.execute(sql)
    rows = cur.fetchall()
    return [d[0] for d in cur.description], rows


@dataclass(frozen=True)
class QualityResult:
    name: str
    failing_rows: int
    columns: list[str]
    sample: list[tuple]

    @property
    def passed(self) -> bool:
        return self.failing_rows == 0


def quality(con: duckdb.DuckDBPyConnection, quality_dir: Path = config.QUALITY_DIR,
            *, sample_size: int = 3, log=print) -> list[QualityResult]:
    results = []
    for path in sorted(quality_dir.glob("*.sql")):
        cur = con.execute(_strip(path.read_text(encoding="utf-8")))
        rows = cur.fetchall()
        r = QualityResult(path.stem, len(rows), [d[0] for d in cur.description], rows[:sample_size])
        results.append(r)
        log(f"[test] {'PASS' if r.passed else 'FAIL'}  {r.name}" + ("" if r.passed else f"  ({r.failing_rows} rows)"))
        if not r.passed:
            log(f"       columns: {', '.join(r.columns)}")
            for row in r.sample:
                log(f"       {row}")
    return results


def markdown_table(columns: list[str], rows: list[tuple]) -> str:
    def fmt(v):
        if v is None:
            return ""
        if isinstance(v, float):
            return f"{v:,.3f}" if abs(v) < 100 else f"{v:,.0f}"
        return str(v)
    head = "| " + " | ".join(columns) + " |"
    sep = "|" + "|".join("---" for _ in columns) + "|"
    return "\n".join([head, sep, *("| " + " | ".join(fmt(v) for v in r) + " |" for r in rows)])
