from __future__ import annotations

import duckdb
import pytest

import fsds_fixture
from efs import load, runner


@pytest.fixture(scope="session")
def archives(tmp_path_factory):
    return fsds_fixture.build(tmp_path_factory.mktemp("fsds"))


@pytest.fixture(scope="session")
def warehouse(archives, tmp_path_factory):
    """Both synthetic quarters loaded and every model built, once per session."""
    staging = tmp_path_factory.mktemp("staging")
    con = duckdb.connect(":memory:")
    load.ensure_raw_schema(con)
    for archive in archives:
        files = load.extract(archive, staging)
        load.load_quarter(con, archive.stem, files, log=lambda *_: None)
    runner.build(con, log=lambda *_: None)
    yield con
    con.close()


def q(con, sql, *params):
    return con.execute(sql, list(params)).fetchall()


def query_rows(con, name, **overrides):
    """Run a showcase query; overrides do literal text substitution (e.g. the as_of date)."""
    from efs import config
    path = next(p for p in config.QUERIES_DIR.glob("*.sql") if p.stem.endswith(name))
    sql = path.read_text(encoding="utf-8")
    for old, new in overrides.items():
        assert old in sql, f"{old!r} not found in {path.name}"
        sql = sql.replace(old, new)
    cur = con.execute(sql.strip().rstrip(";"))
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
