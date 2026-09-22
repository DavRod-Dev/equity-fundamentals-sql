-- A quality screen (ROA, leverage, FCF margin) evaluated using only filings on file as of a chosen date: no look-ahead.
--
-- Edit the as_of date in the first CTE. The screen re-derives each input
-- from core.fact_version with filed <= as_of and re-ranks versions, so a
-- value restated after the date is seen as it was originally filed, and a
-- fiscal year whose 10-K came later does not exist yet. This is the
-- difference between a backtest and a story about a backtest.
WITH params AS (
    SELECT DATE '2025-06-30' AS as_of
),
visible AS (
    SELECT v.cik, c.concept, c.priority, v.period_end, v.value, v.filed, v.adsh
    FROM core.fact_version AS v
    JOIN core.concept AS c
      ON c.tag = v.tag AND c.uom = v.uom AND c.period_type = v.period_type
    CROSS JOIN params
    WHERE v.is_annual
      AND v.qtrs IN (0, 4)
      AND v.filed <= params.as_of
      AND c.concept IN ('revenue', 'net_income', 'operating_cash_flow', 'capex', 'total_assets', 'total_liabilities', 'equity')
),
as_of_version AS (
    -- Latest version *as of the date*, not latest overall.
    SELECT *
    FROM visible
    QUALIFY row_number() OVER (PARTITION BY cik, concept, period_end ORDER BY priority, filed DESC, adsh DESC) = 1
),
statement AS (
    SELECT
        cik,
        period_end,
        max(CASE WHEN concept = 'revenue'             THEN value END) AS revenue,
        max(CASE WHEN concept = 'net_income'          THEN value END) AS net_income,
        max(CASE WHEN concept = 'operating_cash_flow' THEN value END) AS ocf,
        max(CASE WHEN concept = 'capex'               THEN value END) AS capex,
        max(CASE WHEN concept = 'total_assets'        THEN value END) AS total_assets,
        max(CASE WHEN concept = 'equity'              THEN value END) AS equity,
        coalesce(max(CASE WHEN concept = 'total_liabilities' THEN value END),
                 max(CASE WHEN concept = 'total_assets' THEN value END) - max(CASE WHEN concept = 'equity' THEN value END)) AS total_liabilities,
        max(filed)                                                    AS latest_visible_filing
    FROM as_of_version
    GROUP BY cik, period_end
    -- Most recent fiscal year visible as of the date.
    QUALIFY row_number() OVER (PARTITION BY cik ORDER BY period_end DESC) = 1
)
SELECT
    f.filer_name,
    s.cik,
    (SELECT as_of FROM params)                          AS as_of,
    s.period_end                                        AS fiscal_year_end,
    s.latest_visible_filing,
    round(s.net_income / s.total_assets, 3)             AS roa,
    round(s.total_liabilities / s.total_assets, 3)      AS liabilities_to_assets,
    round((s.ocf - s.capex) / s.revenue, 3)             AS fcf_margin
FROM statement AS s
JOIN (SELECT cik, arg_max(filer_name, filed) AS filer_name FROM core.filing GROUP BY cik) AS f USING (cik)
WHERE s.revenue > 0
  AND s.total_assets > 0
  AND s.net_income / s.total_assets       >= 0.05
  AND s.total_liabilities / s.total_assets <= 0.60
  AND (s.ocf - s.capex) / s.revenue       >= 0.10
ORDER BY roa DESC
