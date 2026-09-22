-- view
-- Annual and quarterly reports by domestic filers, one row per filing.
--
-- Amendments (10-K/A, 10-Q/A) are kept: a later model ranks versions of the
-- same period by filing date and lets each query decide whether it wants the
-- latest view or the one that was on file on a given date. prevrpt is SEC's
-- own "superseded" flag and is exposed for convenience, not relied on.
SELECT
    dataset,
    adsh,
    cik,
    name                                   AS filer_name,
    sic,
    CAST(sic / 100 AS INTEGER)             AS sic2,      -- 2-digit industry group
    afs                                    AS filer_status,
    form,
    form LIKE '10-K%'                      AS is_annual,
    period                                 AS period_end, -- balance-sheet date of this filing
    fy                                     AS fiscal_year,
    fp                                     AS fiscal_period,
    fye                                    AS fiscal_year_end_mmdd,
    filed,
    prevrpt                                AS superseded,
    countryba                              AS country,
    stprba                                 AS state
FROM raw.sub
WHERE form IN ('10-K', '10-K/A', '10-Q', '10-Q/A')
  AND period IS NOT NULL
  AND cik IS NOT NULL
