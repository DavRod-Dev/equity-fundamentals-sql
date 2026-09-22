"""Raw layer: archives -> typed tables, idempotently."""
from __future__ import annotations

from datetime import date

from conftest import q
from efs import load
from fsds_fixture import ALPHA, BETA, A8K, B24


def test_extract_pulls_the_four_tables(archives, tmp_path):
    files = load.extract(archives[1], tmp_path)
    assert set(files) == {"sub", "num", "tag", "pre"}
    assert all(p.exists() and p.stat().st_size > 0 for p in files.values())


def test_load_types_columns_and_keeps_every_row(warehouse):
    assert q(warehouse, "SELECT count(*) FROM raw.sub")[0][0] == 8
    (row,) = q(warehouse, "SELECT cik, period, filed, prevrpt, fy FROM raw.sub WHERE adsh = ?", B24)
    assert row == (BETA, date(2024, 12, 31), date(2025, 3, 1), False, 2024)
    (coreg,) = q(warehouse, "SELECT count(*) FROM raw.num WHERE coreg IS NOT NULL")[0]
    assert coreg == 1
    assert q(warehouse, "SELECT DISTINCT dataset FROM raw.num ORDER BY 1") == [("2024q1",), ("2025q1",)]


def test_reloading_a_quarter_replaces_rather_than_appends(warehouse, archives, tmp_path):
    before = q(warehouse, "SELECT count(*) FROM raw.num")[0][0]
    files = load.extract(archives[1], tmp_path)
    load.load_quarter(warehouse, "2025q1", files, log=lambda *_: None)
    assert q(warehouse, "SELECT count(*) FROM raw.num")[0][0] == before
    logs = q(warehouse, "SELECT dataset, \"table\", count(*) FROM raw.load_log GROUP BY ALL ORDER BY ALL")
    assert all(n == 1 for *_, n in logs)


def test_filing_view_keeps_annual_and_quarterly_reports_only(warehouse):
    assert q(warehouse, "SELECT count(*) FROM core.filing WHERE adsh = ?", A8K) == [(0,)]
    forms = dict(q(warehouse, "SELECT form, count(*) FROM core.filing GROUP BY 1"))
    assert forms == {"10-K": 4, "10-Q": 3}


def test_fact_view_excludes_co_registrants_and_non_report_forms(warehouse):
    (beta_assets,) = q(warehouse, """
        SELECT value FROM core.fact WHERE cik = ? AND tag = 'Assets' AND period_end = DATE '2024-12-31'
    """, BETA)
    assert beta_assets == (5000e6,)
    assert q(warehouse, "SELECT count(*) FROM core.fact WHERE adsh = ?", A8K) == [(0,)]
    assert q(warehouse, "SELECT count(*) FROM core.fact WHERE cik = ?", ALPHA)[0][0] == 14 * 4 + 5   # two 10-Ks x (own year + comparative) + five 10-Q values


def test_fact_view_excludes_dimensional_segment_rows(warehouse):
    assert q(warehouse, "SELECT count(*) FROM raw.num WHERE segments IS NOT NULL")[0][0] == 2
    rows = q(warehouse, """
        SELECT value FROM core.fact WHERE cik = ? AND tag = 'Revenues' AND period_end = DATE '2024-12-31' AND qtrs = 4
    """, ALPHA)
    assert rows == [(1210e6,)]
