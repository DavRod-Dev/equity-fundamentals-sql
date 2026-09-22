"""Core models and every showcase query, checked against hand-computed numbers."""
from __future__ import annotations

from datetime import date

import pytest

from conftest import q, query_rows
from efs import runner
from fsds_fixture import ALPHA, BETA, GAMMA, EXPECTED, M


def alpha(rows, year=2024):
    return next(r for r in rows if r["cik"] == ALPHA and r.get("fiscal_year", year) == year)


# ---- core.annual -----------------------------------------------------------

def test_annual_has_one_row_per_filer_fiscal_year(warehouse):
    rows = q(warehouse, "SELECT cik, fiscal_year FROM core.annual ORDER BY 1, 2")
    assert rows == [(ALPHA, 2022), (ALPHA, 2023), (ALPHA, 2024), (BETA, 2024), (GAMMA, 2024)]


def test_annual_picks_latest_10k_version_of_a_comparative(warehouse):
    (ocf,) = q(warehouse, "SELECT operating_cash_flow FROM core.annual WHERE cik = ? AND fiscal_year = 2023", ALPHA)[0]
    assert ocf == 120 * M          # restated in the FY2024 10-K; FY2023 10-K said 100


def test_annual_applies_tag_priority_and_derives_missing_lines(warehouse):
    (rev, liab, gp) = q(warehouse, """
        SELECT revenue, total_liabilities, gross_profit FROM core.annual WHERE cik = ?
    """, BETA)[0]
    assert rev == 500 * M                       # RevenuesNetOfInterestExpense, priority 5
    assert liab == EXPECTED["beta_liabilities"]  # Assets - StockholdersEquity
    assert gp is None                            # no cost of revenue for a bank


def test_annual_labels_52_53_week_year_correctly(warehouse):
    assert q(warehouse, "SELECT fiscal_year, fiscal_year_end FROM core.annual WHERE cik = ?", GAMMA) == [(2024, date(2025, 1, 4))]


def test_fact_version_ranks_and_flags_restatement(warehouse):
    rows = q(warehouse, """
        SELECT version_rank, n_reports, value, first_reported_value, is_latest, is_restated
        FROM core.fact_version
        WHERE cik = ? AND tag = 'NetCashProvidedByUsedInOperatingActivities' AND period_end = DATE '2023-12-31'
        ORDER BY version_rank
    """, ALPHA)
    assert rows == [(1, 2, 120 * M, 100 * M, True, True), (2, 2, 100 * M, 100 * M, False, False)]


# ---- queries -----------------------------------------------------------------

def test_every_query_runs_and_declares_a_purpose(warehouse):
    queries = runner.discover_queries()
    assert len(queries) == 12
    for info in queries:
        assert info.purpose and not info.purpose.startswith("-"), info.name
        cols, _ = runner.run_query(warehouse, info.name, limit=5)
        assert cols, info.name


def test_piotroski_alpha_scores_eight_of_nine(warehouse):
    r = alpha(query_rows(warehouse, "piotroski_f_score"))
    assert r["f_score"] == EXPECTED["alpha_piotroski"]
    assert r["signals_available"] == 9
    assert r["s_turnover_rose"] == 0 and r["s_roa_improved"] == 1 and r["s_no_dilution"] == 1


def test_altman_zones_and_financial_exclusion(warehouse):
    rows = {r["cik"]: r for r in query_rows(warehouse, "altman_z_double_prime")}
    assert BETA not in rows                              # SIC 60-67 excluded
    assert rows[ALPHA]["zone"] == "safe" and rows[ALPHA]["z_double_prime"] == pytest.approx(EXPECTED["alpha_z"], abs=0.01)
    assert rows[GAMMA]["zone"] == "distress" and rows[GAMMA]["z_double_prime"] == pytest.approx(EXPECTED["gamma_z"], abs=0.01)


def test_dupont_identity_holds(warehouse):
    r = alpha(query_rows(warehouse, "dupont"))
    assert r["roe"] == pytest.approx(EXPECTED["alpha_roe"], abs=1e-4)
    assert r["identity_residual"] == pytest.approx(0, abs=1e-9)
    assert r["net_margin"] * r["asset_turnover"] * r["equity_multiplier"] == pytest.approx(r["roe"], abs=1e-3)


def test_growth_uses_the_prior_year_only(warehouse):
    rows = [r for r in query_rows(warehouse, "growth_with_gap_guard") if r["cik"] == ALPHA]
    by_year = {r["fiscal_year"]: r for r in rows}
    assert set(by_year) == {2023, 2024}                  # 2022 has no prior year in the data
    assert by_year[2024]["revenue_growth"] == pytest.approx(EXPECTED["alpha_revenue_growth"], abs=1e-3)
    assert by_year[2024]["net_income_growth"] == pytest.approx(0.5, abs=1e-3)


def test_quarters_derived_from_ytd_add_back_to_the_year(warehouse):
    (r,) = [r for r in query_rows(warehouse, "quarters_from_ytd") if r["cik"] == ALPHA]
    assert (r["q1_mm"], r["q2_mm"], r["q3_mm"], r["q4_mm"]) == EXPECTED["alpha_quarters"]
    assert r["residual"] == 0 and r["fy_mm"] == 1210


def test_restatements_query_finds_the_planted_one(warehouse):
    rows = query_rows(warehouse, "restatements")
    assert [(r["cik"], r["concept"], r["first_reported_mm"], r["latest_mm"]) for r in rows] == [
        (ALPHA, "operating_cash_flow", 100.0, 120.0)
    ]


def test_point_in_time_screen_respects_filing_dates(warehouse):
    visible = query_rows(warehouse, "point_in_time_screen")                      # as of 2025-06-30
    assert [r["cik"] for r in visible] == [ALPHA]
    assert visible[0]["fiscal_year_end"] == date(2024, 12, 31)
    earlier = query_rows(warehouse, "point_in_time_screen", **{"DATE '2025-06-30'": "DATE '2025-01-31'"})
    # Before the FY2024 10-K was filed, only FY2023 is visible: FCF margin 60/1000 fails the screen.
    assert earlier == []


def test_tag_adoption_counts_filers_per_tag(warehouse):
    # The population floor is a display choice for live data; the fixture has three filers.
    rows = {(r["fiscal_year"], r["tag"]): r["filers"]
            for r in query_rows(warehouse, "tag_adoption", **{"filers_in_year >= 100": "filers_in_year >= 1"})}
    assert rows[(2024, "Revenues")] == 2 and rows[(2024, "RevenuesNetOfInterestExpense")] == 1


def test_completeness_audit_reports_the_bank_gaps(warehouse):
    rows = {(r["fiscal_year"], r["concept"]): r["coverage"] for r in query_rows(warehouse, "completeness_audit")}
    assert rows[(2024, "net_income")] == 1.0
    assert rows[(2024, "total_liabilities")] == 1.0     # derived for Beta, so still covered
    assert rows[(2024, "capex")] == pytest.approx(2 / 3, abs=1e-3)


def test_all_quality_assertions_pass_on_fixture(warehouse):
    results = runner.quality(warehouse, log=lambda *_: None)
    assert len(results) == 11
    assert [r.name for r in results if not r.passed] == []
