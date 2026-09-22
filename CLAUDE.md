# CLAUDE.md

Project rules for Claude Code, and a plain account of how this repo was built
with it.

## Conventions the tool must keep

- **SQL first.** Python here fetches, loads and runs files. If a change
  needs pandas, it is a SQL change in disguise; put it in `sql/`.
- **Model files declare their materialisation on line 1**: `-- view` or
  `-- table`. The object is `core.<filename without numeric prefix>`.
  `src/efs/runner.py` is the only code that knows this.
- **Query files declare their purpose on line 1** as a comment. That line
  is what `python -m efs list` prints; keep it one sentence.
- **Every query is exercised by the offline suite** against the synthetic
  archives in `tests/fsds_fixture.py`, with at least one hand-computed
  number. A query that only "runs" is not tested.
- **Never key facts on `fy`/`fp`.** Those describe the filing. Key on
  `ddate` (period end) and `qtrs`. `sub.period` is the balance-sheet date
  of the filing and is the right anchor for annual selection.
- **`coreg IS NULL AND segments IS NULL` everywhere facts are read.**
  Co-registrant rows duplicate consolidated tags for subsidiaries;
  dimensional rows (segments, geographies, eliminations) share the tag and
  period of the total they break down. `core.fact` applies both filters and
  nothing downstream should read `raw.num` directly.
- **No secrets, no contact details, no data in git.** `SEC_USER_AGENT` comes
  from the environment with no default; `data/` is ignored and reproducible.

## How this was built

One Claude Code session. The human chose the data source (the SEC bulk
Financial Statement Data Sets rather than the per-company JSON API, because
they are relational and cover every filer), the analytical targets
(Piotroski, Altman, DuPont, point-in-time screening, quarterly derivation),
and the rule that this repository shares nothing with any other project.

The model wrote the loader, the models, the twelve queries and the fixture,
in that order, with each layer syntax-checked before the next. The fixture
was designed so that every query has a hand-checkable answer (Alpha Widgets
scores exactly 8 of 9 on Piotroski because its asset turnover fell from
1.111 to 1.100); the tests then held the SQL to those numbers.

SEC returned HTTP 403 ("Request Rate Threshold Exceeded") for every request
during development. It was not a rate limit: the contact address in the
User-Agent contained the substring "github", which SEC's bot filter rejects
outright while showing the rate-limit page. Diagnosing that took a
controlled comparison of User-Agent strings, and the answer is now enforced
in `config.user_agent()` and explained by `fetch.py`'s 403 message. The
pipeline was finished and green against synthetic data before a byte of real
data was loaded, which is the right order anyway. What the real data then
changed is recorded in `README.md` under *Design notes*.
