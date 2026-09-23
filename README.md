# equity-fundamentals-sql

Analytical SQL over the SEC's Financial Statement Data Sets: every XBRL
statement filed by every public company, loaded into DuckDB as four
relational tables, with twelve showcase queries on top. Piotroski and Altman
scores, sector percentiles, DuPont, quarterly figures derived from
year-to-date filings, restatement detection and a point-in-time screen —
all in SQL, all tested against hand-computed answers.

[![ci](https://github.com/davrod-dev/equity-fundamentals-sql/actions/workflows/ci.yml/badge.svg)](https://github.com/davrod-dev/equity-fundamentals-sql/actions/workflows/ci.yml)

Python does three things here — fetch, load, run files — in about 350
lines. Everything with a financial opinion lives in [`sql/`](sql/).

## Quickstart

```bash
git clone https://github.com/davrod-dev/equity-fundamentals-sql
cd equity-fundamentals-sql
pip install -e ".[dev]"

# SEC requires a User-Agent with a contact address. No default, on purpose.
# (And not one containing "github": SEC's bot filter answers 403 to that. Design note 2.)
export SEC_USER_AGENT="equity-fundamentals-sql you@example.com"   # PowerShell: $env:SEC_USER_AGENT = "..."

python -m efs load       # fetch config/quarters.json archives (~60 MB each) and load raw tables
python -m efs build      # create core.* views and tables from sql/models
python -m efs test       # run tests/quality/*.sql; any returned row is a failure
python -m efs list       # the twelve queries and what each answers
python -m efs query piotroski_f_score --limit 20
pytest                   # offline suite; never touches sec.gov
```

## The queries

| # | query | answers |
|---|---|---|
| 01 | `universe` | who is in the data: filings, filers and date range by quarter, form and SEC size class |
| 02 | `annual_statement` | latest fiscal year per filer, key lines in $mm — the base table |
| 03 | `sector_percentiles` | where each filer sits within its 2-digit SIC group: percentile and decile of margin, ROA, FCF margin (groups under 20 dropped) |
| 04 | `growth_with_gap_guard` | YoY growth that returns NULL, not a two-year number, when a year is missing |
| 05 | `piotroski_f_score` | the nine-signal F-score with average balances, and how many signals could be evaluated |
| 06 | `altman_z_double_prime` | the book-value Altman variant (no prices needed) with safe / grey / distress zones; financials excluded |
| 07 | `dupont` | ROE = margin × turnover × leverage on average balances, with the identity residual shown |
| 08 | `quarters_from_ytd` | standalone Q1–Q4 from cumulative 10-Q values and the 10-K, proven to add back to the year |
| 09 | `restatements` | key lines whose latest filed value differs from the first reported one by ≥ 1 % and ≥ $10mm |
| 10 | `point_in_time_screen` | a quality screen evaluated using only filings on file as of a chosen date |
| 11 | `tag_adoption` | how revenue tag usage shifted by fiscal year — taxonomy churn measured |
| 12 | `completeness_audit` | share of filers with each concept populated, via UNPIVOT — where the map is thin |

Each file starts with a one-line purpose (what `efs list` prints) and a
comment explaining the technique and its caveats. They are meant to be read.

## What comes out

Four quarters of data sets (2025q1 to 2025q4), on a laptop: 26,085 filings
and 14.6 million numeric values load in about a minute from cached archives
(the downloads themselves are ~400 MB); 5.1 million of the values are
consolidated, non-dimensional facts from 22,731 10-K and 10-Q filings, and
they resolve to 16,340 filer-years in `core.annual`. `build` takes 15 s and
the eleven assertions 20 s. Everything below is real output, as of
September 2026, columns trimmed to fit.

**`annual_statement`** — largest filers by latest-year revenue, $mm:

| filer_name | fiscal_year_end | revenue_mm | operating_income_mm | net_income_mm | fcf_mm | assets_mm | equity_mm |
|---|---|---|---|---|---|---|---|
| WALMART INC. | 2025-01-31 | 680,985 | 29,348 | 19,436 | 12,660 | 260,823 | 91,013 |
| AMAZON COM INC | 2024-12-31 | 637,959 | 68,593 | 59,248 | 32,878 | 624,894 | 285,970 |
| APPLE INC | 2025-09-30 | 416,161 | 133,050 | 112,010 | 98,767 | 359,241 | 73,733 |
| UNITEDHEALTH GROUP INC | 2024-12-31 | 400,278 | 32,287 | 14,405 | 20,705 | 298,278 | 98,268 |
| CVS HEALTH CORP | 2024-12-31 | 372,809 | 8,516 | 4,614 | 6,326 | 253,215 | 75,560 |
| BERKSHIRE HATHAWAY INC | 2024-12-31 | 371,433 |  | 88,995 | 11,616 | 1,153,881 | 649,368 |
| ALPHABET INC. | 2024-12-31 | 350,018 | 112,390 | 100,118 | 72,764 | 450,256 | 325,084 |
| MICROSOFT CORP | 2025-06-30 | 281,724 | 128,528 | 101,832 | 71,611 | 619,003 | 343,479 |

Berkshire's blank operating income is a correct blank: it reports none.

**`quarters_from_ytd`** — standalone quarters recovered from cumulative
filings, $mm. The residual column (q1+q2+q3+q4 − fy) is zero on every row:

| filer_name | fiscal_year_end | q1_mm | q2_mm | q3_mm | q4_mm | fy_mm | q4_share_of_year |
|---|---|---|---|---|---|---|---|
| WALMART INC. | 2025-01-31 | 161,508 | 169,335 | 169,588 | 180,554 | 680,985 | 0.265 |
| AMAZON COM INC | 2024-12-31 | 143,313 | 147,977 | 158,877 | 187,792 | 637,959 | 0.294 |
| APPLE INC | 2025-09-30 | 124,300 | 95,359 | 94,036 | 102,466 | 416,161 | 0.246 |
| ALPHABET INC. | 2024-12-31 | 80,539 | 84,742 | 88,268 | 96,469 | 350,018 | 0.276 |
| EXXON MOBIL CORP | 2024-12-31 | 83,083 | 93,060 | 90,016 | 83,426 | 349,585 | 0.239 |

Apple's fiscal Q1 is the holiday quarter; Amazon's Q4 is 29 % of its year.
Neither figure is filed anywhere — both are differences of filed values.

**`piotroski_f_score`** — the only 9-of-9 in the data, and the 8s:

| filer_name | fiscal_year | f_score | s_roa_improved | s_leverage_fell | s_liquidity_rose | s_no_dilution | s_margin_rose | s_turnover_rose |
|---|---|---|---|---|---|---|---|---|
| DORMAN PRODUCTS, INC. | 2024 | 9 | 1 | 1 | 1 | 1 | 1 | 1 |
| AUTOMATIC DATA PROCESSING INC | 2025 | 8 | 1 | 0 | 1 | 1 | 1 | 1 |
| CINTAS CORP | 2025 | 8 | 1 | 0 | 1 | 1 | 1 | 1 |
| COSTCO WHOLESALE CORP /NEW | 2025 | 8 | 1 | 1 | 1 | 0 | 1 | 1 |
| MSA SAFETY INC | 2024 | 8 | 1 | 1 | 1 | 1 | 0 | 1 |
| AMAZON COM INC | 2024 | 7 | 1 | 1 | 1 | 0 | 1 | 0 |

**`point_in_time_screen`** as of 2025-06-30 — ROA ≥ 5 %, liabilities ≤ 60 %
of assets, FCF margin ≥ 10 %, using only filings on file that day:

| filer_name | fiscal_year_end | latest_visible_filing | roa | liabilities_to_assets | fcf_margin |
|---|---|---|---|---|---|
| NVIDIA CORP | 2025-01-31 | 2025-02-26 | 0.653 | 0.289 | 0.466 |
| MONOLITHIC POWER SYSTEMS INC | 2024-12-31 | 2025-03-03 | 0.494 | 0.130 | 0.291 |
| PINTEREST, INC. | 2024-12-31 | 2025-02-06 | 0.349 | 0.111 | 0.258 |
| DECKERS OUTDOOR CORP | 2025-03-31 | 2025-05-23 | 0.271 | 0.296 | 0.192 |
| NVR INC | 2024-12-31 | 2025-02-12 | 0.264 | 0.340 | 0.128 |

**`altman_z_double_prime`** — most distressed among filers with ≥ $100mm of
assets. Viavi's retained earnings are −35× its assets: the accumulated
deficit of the dot-com era, still on the balance sheet.

| filer_name | sic2 | fiscal_year | wc_to_assets | re_to_assets | ebit_to_assets | equity_to_liabilities | z_double_prime | zone |
|---|---|---|---|---|---|---|---|---|
| VIAVI SOLUTIONS INC. | 37 | 2025 | 0.148 | -34.922 | 0.029 | 0.643 | -112 | distress |
| ATARA BIOTHERAPEUTICS, INC. | 28 | 2024 | -0.639 | -18.832 | -0.765 | -0.471 | -71.2 | distress |
| MULLEN AUTOMOTIVE INC. | 37 | 2024 | -0.672 | -12.983 | -2.193 | -0.146 | -61.6 | distress |
| 23ANDME HOLDING CO. | 28 | 2025 | 0.188 | -15.347 | -1.505 | -0.143 | -59.1 | distress |

**`restatements`** — largest first-vs-latest differences on dollar lines:

| filer_name | concept | period_end | first_reported_mm | latest_mm | pct_change | n_reports |
|---|---|---|---|---|---|---|
| FANNIE MAE | cash | 2024-12-31 | 78,811 | 38,536 | -0.511 | 4 |
| BROOKFIELD ASSET MANAGEMENT LTD. | total_assets | 2024-12-31 | 4,386 | 14,157 | 2.228 | 4 |
| MECHANICS BANCORP | total_assets | 2024-12-31 | 8,124 | 16,490 | 1.030 | 4 |
| GALAXY DIGITAL INC. | total_assets | 2024-12-31 | 0.000 | 7,120 |  | 3 |

Brookfield and Mechanics are post-merger recasts; Galaxy first filed a
zero. None are errors in this pipeline — they are what the filings say.

**`tag_adoption`** — the reason `core.concept` exists. Seven years after
ASC 606, four in ten filers still use the older `Revenues` tag:

| fiscal_year | tag | filers | share_of_filers |
|---|---|---|---|
| 2024 | RevenueFromContractWithCustomerExcludingAssessedTax | 2,224 | 0.563 |
| 2024 | Revenues | 1,690 | 0.428 |
| 2024 | RevenuesNetOfInterestExpense | 35 | 0.009 |

**`completeness_audit`**, fiscal 2025 — where the map is thin. Long-term
debt at 32 % is the standout: filers spread it across a dozen tags this map
does not yet cover, so any screen on leverage should say so.

| concept | coverage | | concept | coverage |
|---|---|---|---|---|
| net_income | 0.990 | | revenue | 0.766 |
| equity | 0.979 | | shares_outstanding | 0.747 |
| operating_cash_flow | 0.962 | | capex | 0.725 |
| current_assets | 0.893 | | gross_profit | 0.677 |
| operating_income | 0.827 | | long_term_debt | 0.323 |

## The data, and the model on top of it

SEC publishes one zip per calendar quarter holding every numeric value from
every XBRL financial statement filed in that quarter, as four tab-separated
tables:

```
sub   one row per filing        adsh (accession no.), cik, name, sic, form, period, fy, fp, filed, ...
num   one row per value         adsh, tag, version, coreg, segments, ddate, qtrs, uom, value
tag   tag definitions           tag, version, datatype, iord (instant/duration), crdr, label
pre   statement presentation    adsh, stmt (BS/IS/CF/...), line, tag, label
```

`num` is the interesting one. `ddate` is the period end, `qtrs` is 0 for a
balance-sheet instant and otherwise the duration in quarters, `segments`
is empty for the consolidated total and populated for every dimensional
breakdown of it, and a 10-K carries its comparatives too — so one filing
yields two or three fiscal years, and one quarter of data yields a usable
history.

```
 data/raw/<quarter>.zip                exact archive as published
        │  src/efs/load.py            extract; read all-text; TRY_CAST on insert; replace per quarter
        ▼
 raw.sub  raw.num  raw.tag  raw.pre   typed, with a dataset column
        │  src/efs/runner.py          sql/models in order; line 1 says view or table
        ▼
 core.filing        10-K and 10-Q families, typed dates, 2-digit SIC          (view)
 core.fact          consolidated, non-dimensional values with their filing    (view)
 core.fact_version  every version of every fact, ranked by filing date        (table)
 core.concept       line item ↔ XBRL tag(s), with priority, unit, period type (table)
 core.annual        one row per filer per fiscal year, latest 10-K view       (table)
        │  tests/quality/*.sql        11 assertions; zero rows = pass
        ▼
 sql/queries/*.sql                     the twelve above
```

### Why versions are kept

The same (filer, concept, period) is reported first in its own 10-K, again
as a comparative in the next one, and again in any amendment. Most quick
scripts keep the last row or the first and get quietly different answers.
`core.fact_version` keeps all of them with `version_rank`, `n_reports`,
`first_reported_value`, `is_latest` and `is_restated`, so:

- `core.annual` takes the latest 10-K view (a dashboard wants what we know now);
- `restatements` compares first and latest (an auditor wants what changed);
- `point_in_time_screen` re-ranks with `filed <= as_of` (a backtest wants
  what was knowable then).

Same table, three deliberate choices. See
[`sql/models/03_fact_version.sql`](sql/models/03_fact_version.sql).

## Design notes: what the data taught this repo

Each began as a failing assertion or an absurd number on live data, and
each was fixed in the model or the map, never by loosening the check to
make red go green. The fixture gained a case for most of them.

1. **`num` has a `segments` column, and it is the whole game.** Since 2020
   the data sets carry dimensional facts — revenue by segment, assets by
   geography, elimination lines — in the same table, same tag, same period
   as the consolidated total. The first live run read them as totals:
   Walmart showed a gross profit of −$244 billion, JPMorgan $638 million of
   assets, and 1.58 million "duplicate" keys. `core.fact` now requires
   `segments IS NULL` alongside `coreg IS NULL`, and nothing downstream
   reads `raw.num`.
2. **SEC's 403 is not always a rate limit.** Every request returned
   "Request Rate Threshold Exceeded" — for a User-Agent that contained the
   substring `github` in its contact address. A controlled comparison of
   strings isolated the token; `config.user_agent()` now refuses it with an
   explanation, since SEC will not.
3. **A 10-K carries more balance sheets than its year end.** Selected
   quarterly data and subsequent-events notes put instants at quarter ends
   into the same filing, which the annual model read as four fiscal years
   in one calendar year. Only the filing's own period end and the
   comparatives 12 and 24 months earlier (±10 days for 52/53-week
   calendars) are now admitted.
4. **Duplicate fiscal-year labels have one honest cause.** Filers that
   changed their year end have a transition period and a full year in one
   calendar year. The one-row-per-label assertion excludes filers whose
   10-Ks show more than one `fye`, and the growth queries guard with a
   year check regardless.
5. **Some facts are dated in the future on purpose.** Declared dividends
   carry their payment date. "Filed after period end" is asserted on the
   annual statement, where every fact is a reported figure, not on `raw.num`.
6. **Negative revenue is real.** Commodity funds, run-off insurers and
   mortgage REITs book investment losses through `Revenues`; two
   pre-commercial biotechs reversed collaboration revenue. The assertion
   now excludes SIC 60–69 and anything under $10 million.
7. **Assets = liabilities + equity is not assertable from these tags.**
   Temporary (mezzanine) equity — redeemable preferred, redeemable NCI —
   sits between the two: Reddit, ServiceTitan and NuScale all "failed" by
   more than 60 % of assets. What is asserted instead: the filer's own
   `LiabilitiesAndStockholdersEquity` equals its `Assets`, and total equity
   including NCI does not exceed assets. Parent-only equity *can* exceed
   assets when NCI is negative (Up-C structures), which NuScale demonstrated.
8. **SEC's own files contain duplicate rows** — a few hundred per quarter,
   all among dimensional facts with free-text member names (counterparties
   in derivatives tables). The natural-key assertion is scoped to the
   consolidated rows this repository reads.
9. **`percent_rank` sorts NULLs last, which means "best".** A filer with no
   capex figure ranked as the top free-cash-flow margin in its sector. Each
   rank now partitions on whether the metric is NULL and returns NULL for
   the NULL side.
10. **`CREATE TABLE IF NOT EXISTS` does not migrate.** Adding the
    `segments` column to a database created before it produced a binder
    error on insert. `ensure_raw_schema` now checks for the column and
    says to delete the file; the data is reproducible.
11. **Shell companies break every ratio.** Z-scores of −2.3 million, equity
    multipliers of 300, revenue growth of 3,000 % off a $3 million base.
    The ranking queries carry explicit floors — $100 million of assets or
    revenue, equity at least 5 % of assets — stated in their headers.
12. **Filings contain scale errors.** Crinetics reported 32.3 shares
    outstanding in one filing and 32.3 million in the next. The restatement
    query is restricted to dollar lines; the share count stays in the data
    with its `is_restated` flag for anyone who wants it.

## Testing

`tests/fsds_fixture.py` builds two synthetic quarterly archives in the exact
SEC layout — column headers, tab separation, YYYYMMDD dates, a co-registrant
row, two segment-member rows of a revenue total, an 8-K that must be
ignored, three 10-Qs with quarter and year-to-date values, a 52/53-week
year ending on 4 January, and one comparative restated in the following
10-K. Three filers were designed so that every query has a
hand-checkable answer: Alpha Widgets scores exactly 8 of 9 on Piotroski
because its asset turnover slipped from 1.111 to 1.100; its Z″ is 5.26;
its four derived quarters are 250 / 300 / 350 / 310 and sum to the reported
1,210. Twenty-six tests hold the SQL to those numbers, and CI runs them on
Python 3.11 and 3.12 without network access.

The eleven SQL assertions in [`tests/quality/`](tests/quality/) run against
whatever is loaded — synthetic or real — and print the offending rows when
they fail.

## Built with Claude Code

Written in one session with Claude Code doing the typing and first drafts;
the human chose the data source, the analytical targets and what to ship,
and reviewed every query against the SEC documentation. The pipeline was
finished and green on synthetic data before any real data was loaded, and
the twelve design notes above are what the real data then changed. [`CLAUDE.md`](CLAUDE.md) records the conventions and the
process.

## Not done, on purpose

- **Market data.** No prices, so no valuation multiples and the classic
  Altman Z (which needs market cap) is replaced by Z″. Adding a price table
  is a load step, not a redesign.
- **Notes and dimensions.** The statement data sets omit segment and
  geographic breakdowns; those are in the larger Notes data sets.
- **Custom tags.** Filer-specific tags (`version` = the filing's own
  accession number) are loaded but unmapped. `completeness_audit` shows
  where that matters.

## License

MIT. Source data is published by the U.S. Securities and Exchange
Commission and is public domain; the
[fair-access policy](https://www.sec.gov/os/accessing-edgar-data) applies to
fetching it.

---

David Rodriguez · [github.com/davrod-dev](https://github.com/davrod-dev)
