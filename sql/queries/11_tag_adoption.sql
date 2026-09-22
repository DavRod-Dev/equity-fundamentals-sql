-- How revenue tag usage shifted across fiscal years: taxonomy churn measured, not assumed.
--
-- The concept map exists because of this. A pipeline that hard-codes
-- "Revenues" silently loses most filers after 2018, when ASC 606 moved them
-- to RevenueFromContractWithCustomerExcludingAssessedTax.
WITH annual_revenue_tags AS (
    SELECT DISTINCT
        v.cik,
        year(v.period_end - INTERVAL 7 DAY) AS fiscal_year,
        v.tag
    FROM core.fact_version AS v
    JOIN core.concept AS c
      ON c.tag = v.tag AND c.uom = v.uom AND c.period_type = v.period_type
    WHERE c.concept = 'revenue'
      AND v.is_annual
      AND v.qtrs = 4
      AND v.is_latest
)
SELECT
    fiscal_year,
    tag,
    count(DISTINCT cik)                                                            AS filers,
    round(count(DISTINCT cik) * 1.0 / sum(count(DISTINCT cik)) OVER (PARTITION BY fiscal_year), 3) AS share_of_filers
FROM annual_revenue_tags
GROUP BY fiscal_year, tag
ORDER BY fiscal_year, filers DESC
