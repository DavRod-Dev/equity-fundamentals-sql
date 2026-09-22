# equity-fundamentals-sql

Analytical SQL over the SEC's Financial Statement Data Sets: every XBRL
statement filed by every public company, loaded into DuckDB as four
relational tables, with twelve showcase queries on top. Piotroski and Altman
scores, sector percentiles, DuPont, quarterly figures derived from
year-to-date filings, restatement detection and a point-in-time screen —
all in SQL, all tested against hand-computed answers.

[![ci](https://github.com/david-rodriguez-dev/equity-fundamentals-sql/actions/workflows/ci.yml/badge.svg)](https://github.com/david-rodriguez-dev/equity-fundamentals-sql/actions/workflows/ci.yml)

Python does three things here — fetch, load, run files — in about 350
lines. Everything with a financial opinion lives in [`sql/`](sql/).

## Quickstart

```bash
git clone https://github.com/david-rodriguez-dev/equity-fundamentals-sql
cd equity-fundamentals-sql
pip install -e ".[dev]"

# SEC requires a User-Agent with a contact address. No default, on purpose.
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

<!-- LIVE_RESULTS -->

## The data, and the model on top of it

SEC publishes one zip per calendar quarter holding every numeric value from
every XBRL financial statement filed in that quarter, as four tab-separated
tables:

```
sub   one row per filing        adsh (accession no.), cik, name, sic, form, period, fy, fp, filed, ...
num   one row per value         adsh, tag, version, coreg, ddate, qtrs, uom, value
tag   tag definitions           tag, version, datatype, iord (instant/duration), crdr, label
pre   statement presentation    adsh, stmt (BS/IS/CF/...), line, tag, label
```

`num` is the interesting one. `ddate` is the period end, `qtrs` is 0 for a
balance-sheet instant and otherwise the duration in quarters, and a 10-K
carries its comparatives too — so one filing yields two or three fiscal
years, and one quarter of data yields a usable history.

```
 data/raw/<quarter>.zip                exact archive as published
        │  src/efs/load.py            extract; read all-text; TRY_CAST on insert; replace per quarter
        ▼
 raw.sub  raw.num  raw.tag  raw.pre   typed, with a dataset column
        │  src/efs/runner.py          sql/models in order; line 1 says view or table
        ▼
 core.filing        10-K and 10-Q families, typed dates, 2-digit SIC          (view)
 core.fact          consolidated values joined to their filing                (view)
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

<!-- DESIGN_NOTES -->

## Testing

`tests/fsds_fixture.py` builds two synthetic quarterly archives in the exact
SEC layout — column headers, tab separation, YYYYMMDD dates, a co-registrant
row, an 8-K that must be ignored, three 10-Qs with quarter and year-to-date
values, a 52/53-week year ending on 4 January, and one comparative restated
in the following 10-K. Three filers were designed so that every query has a
hand-checkable answer: Alpha Widgets scores exactly 8 of 9 on Piotroski
because its asset turnover slipped from 1.111 to 1.100; its Z″ is 5.26;
its four derived quarters are 250 / 300 / 350 / 310 and sum to the reported
1,210. Twenty-one tests hold the SQL to those numbers, and CI runs them on
Python 3.11 and 3.12 without network access.

The eleven SQL assertions in [`tests/quality/`](tests/quality/) run against
whatever is loaded — synthetic or real — and print the offending rows when
they fail.

## Built with Claude Code

Written in one session with Claude Code doing the typing and first drafts;
the human chose the data source, the analytical targets and what to ship,
and reviewed every query against the SEC documentation. SEC rate-limited
the machine partway through, so the pipeline was finished and green on
synthetic data before any real data was loaded — the order it should have
been in anyway. [`CLAUDE.md`](CLAUDE.md) records the conventions and the
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

David Rodriguez · [github.com/david-rodriguez-dev](https://github.com/david-rodriguez-dev)
