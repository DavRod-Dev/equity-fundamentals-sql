-- Altman Z''-score (the book-value variant that needs no market prices) with distress zones, latest fiscal year per filer.
--
--   Z'' = 6.56 * working capital / assets
--       + 3.26 * retained earnings / assets
--       + 6.72 * EBIT / assets
--       + 1.05 * book equity / total liabilities
--
-- Zones per Altman (1995): above 2.6 safe, 1.1 to 2.6 grey, below 1.1 distress.
-- EBIT is operating income where reported, else pretax income plus interest.
-- Financials (SIC 60-67) are excluded: the model was never meant for balance
-- sheets that are mostly customer deposits and loans. So are filers with
-- under $100 million of assets: shell companies with a few thousand dollars
-- of assets and years of accumulated deficit produce Z-scores in the
-- negative millions, which is arithmetic, not insight.
WITH latest AS (
    SELECT *
    FROM core.annual
    WHERE total_assets >= 1e8
      AND total_liabilities > 0
      AND sic2 NOT BETWEEN 60 AND 67
    QUALIFY row_number() OVER (PARTITION BY cik ORDER BY fiscal_year_end DESC) = 1
),
components AS (
    SELECT
        cik,
        filer_name,
        sic2,
        fiscal_year,
        working_capital   / total_assets                                    AS x1,
        retained_earnings / total_assets                                    AS x2,
        coalesce(operating_income, pretax_income + interest_expense)
                          / total_assets                                    AS x3,
        equity            / total_liabilities                               AS x4
    FROM latest
)
SELECT
    filer_name,
    cik,
    sic2,
    fiscal_year,
    round(x1, 3) AS wc_to_assets,
    round(x2, 3) AS re_to_assets,
    round(x3, 3) AS ebit_to_assets,
    round(x4, 3) AS equity_to_liabilities,
    round(6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4, 2)                 AS z_double_prime,
    CASE
        WHEN 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4 > 2.6  THEN 'safe'
        WHEN 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4 >= 1.1 THEN 'grey'
        ELSE 'distress'
    END                                                                     AS zone
FROM components
WHERE x1 IS NOT NULL AND x2 IS NOT NULL AND x3 IS NOT NULL AND x4 IS NOT NULL
ORDER BY z_double_prime
