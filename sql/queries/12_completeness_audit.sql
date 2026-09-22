-- Share of filers with each core concept populated, per fiscal year: where the concept map is thin.
--
-- UNPIVOT turns the wide annual table into (concept, is_present) rows so
-- one GROUP BY answers the question for every concept at once. A concept
-- well under 90 % is either genuinely optional (interest expense) or a tag
-- the map is missing; either way this is the first thing to look at before
-- trusting a screen built on it.
WITH long AS (
    UNPIVOT (
        SELECT
            cik,
            fiscal_year,
            revenue IS NOT NULL             AS revenue,
            gross_profit IS NOT NULL        AS gross_profit,
            operating_income IS NOT NULL    AS operating_income,
            net_income IS NOT NULL          AS net_income,
            operating_cash_flow IS NOT NULL AS operating_cash_flow,
            capex IS NOT NULL               AS capex,
            total_assets IS NOT NULL        AS total_assets,
            current_assets IS NOT NULL      AS current_assets,
            current_liabilities IS NOT NULL AS current_liabilities,
            total_liabilities IS NOT NULL   AS total_liabilities,
            equity IS NOT NULL              AS equity,
            retained_earnings IS NOT NULL   AS retained_earnings,
            long_term_debt IS NOT NULL      AS long_term_debt,
            shares_outstanding IS NOT NULL  AS shares_outstanding
        FROM core.annual
    )
    ON revenue, gross_profit, operating_income, net_income, operating_cash_flow, capex,
       total_assets, current_assets, current_liabilities, total_liabilities, equity,
       retained_earnings, long_term_debt, shares_outstanding
    INTO NAME concept VALUE is_present
)
SELECT
    fiscal_year,
    concept,
    count(*)                                          AS filer_years,
    sum(is_present::INT)                              AS populated,
    round(sum(is_present::INT) * 1.0 / count(*), 3)   AS coverage
FROM long
GROUP BY ALL
ORDER BY fiscal_year DESC, coverage
