-- Standalone quarterly revenue derived from cumulative filings: 10-Qs report year-to-date, and Q4 is never filed at all.
--
-- A fiscal year in FSDS looks like: Q1 (qtrs=1), six months (qtrs=2), nine
-- months (qtrs=3) from the three 10-Qs, and the full year (qtrs=4) from the
-- 10-K. Each YTD figure is matched to its fiscal year by distance from the
-- year end, with a two-week tolerance for 52/53-week calendars, and the
-- standalone quarters are successive differences. The final column proves
-- the four quarters add back to the reported year.
WITH revenue AS (
    SELECT v.cik, v.period_end, v.qtrs, v.value
    FROM core.fact_version AS v
    JOIN core.concept AS c
      ON c.tag = v.tag AND c.uom = v.uom AND c.period_type = v.period_type
    WHERE c.concept = 'revenue'
      AND v.is_latest
      AND v.qtrs BETWEEN 1 AND 4
    QUALIFY row_number() OVER (PARTITION BY v.cik, v.period_end, v.qtrs ORDER BY c.priority) = 1
),
fiscal_years AS (
    SELECT cik, period_end AS fiscal_year_end, value AS fy_revenue
    FROM revenue
    WHERE qtrs = 4
),
ytd AS (
    SELECT
        f.cik,
        f.fiscal_year_end,
        f.fy_revenue,
        r.qtrs,
        r.value
    FROM fiscal_years AS f
    JOIN revenue AS r
      ON r.cik = f.cik
     AND r.qtrs < 4
     AND abs(date_diff('day', r.period_end, f.fiscal_year_end) - (4 - r.qtrs) * 91) <= 14
),
pivoted AS (
    SELECT
        cik,
        fiscal_year_end,
        fy_revenue,
        max(CASE WHEN qtrs = 1 THEN value END) AS ytd_q1,
        max(CASE WHEN qtrs = 2 THEN value END) AS ytd_q2,
        max(CASE WHEN qtrs = 3 THEN value END) AS ytd_q3
    FROM ytd
    GROUP BY ALL
)
SELECT
    a.filer_name,
    p.cik,
    p.fiscal_year_end,
    round(p.ytd_q1 / 1e6, 1)                     AS q1_mm,
    round((p.ytd_q2 - p.ytd_q1) / 1e6, 1)        AS q2_mm,
    round((p.ytd_q3 - p.ytd_q2) / 1e6, 1)        AS q3_mm,
    round((p.fy_revenue - p.ytd_q3) / 1e6, 1)    AS q4_mm,
    round(p.fy_revenue / 1e6, 1)                 AS fy_mm,
    round((p.fy_revenue - p.ytd_q3) / p.fy_revenue, 3) AS q4_share_of_year,
    -- identity: q1 + q2 + q3 + q4 = fy, by construction; shown so it is visibly true
    round(p.ytd_q1 + (p.ytd_q2 - p.ytd_q1) + (p.ytd_q3 - p.ytd_q2) + (p.fy_revenue - p.ytd_q3) - p.fy_revenue, 2) AS residual
FROM pivoted AS p
JOIN core.annual AS a ON a.cik = p.cik AND a.fiscal_year_end = p.fiscal_year_end
WHERE p.ytd_q1 IS NOT NULL AND p.ytd_q2 IS NOT NULL AND p.ytd_q3 IS NOT NULL AND p.fy_revenue > 0
ORDER BY p.fy_revenue DESC
