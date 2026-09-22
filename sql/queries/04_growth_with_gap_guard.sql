-- Year-over-year revenue and net income growth per filer; NULL rather than wrong when the prior year is missing.
--
-- LAG reaches back one ROW, not one YEAR. If a filer is missing fiscal 2023,
-- a naive LAG compares 2024 with 2022 and reports two years of growth as
-- one. Every prior value here is wrapped in a check that the previous row
-- really is the previous fiscal year.
WITH lagged AS (
    SELECT
        cik,
        filer_name,
        fiscal_year,
        revenue,
        net_income,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1 THEN lag(revenue)    OVER w END AS revenue_prior,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1 THEN lag(net_income) OVER w END AS net_income_prior
    FROM core.annual
    WINDOW w AS (PARTITION BY cik ORDER BY fiscal_year_end)
)
SELECT
    filer_name,
    cik,
    fiscal_year,
    round(revenue / 1e6, 1)                                     AS revenue_mm,
    round(revenue / nullif(revenue_prior, 0) - 1, 3)            AS revenue_growth,
    round(net_income / 1e6, 1)                                  AS net_income_mm,
    -- Growth off a loss is not meaningful; report the swing in $ instead.
    CASE WHEN net_income_prior > 0
         THEN round(net_income / net_income_prior - 1, 3) END   AS net_income_growth,
    round((net_income - net_income_prior) / 1e6, 1)             AS net_income_change_mm
FROM lagged
WHERE revenue_prior IS NOT NULL
ORDER BY revenue_growth DESC NULLS LAST
