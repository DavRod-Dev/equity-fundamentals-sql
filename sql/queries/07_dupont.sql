-- DuPont decomposition: ROE as net margin x asset turnover x equity multiplier, on average balances.
--
-- The three factors multiply back to ROE exactly, which the last column
-- checks. Using average rather than closing balances is what makes the
-- identity hold for a company whose balance sheet moved during the year.
WITH avg_bal AS (
    SELECT
        cik, filer_name, fiscal_year, revenue, net_income,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1
             THEN (total_assets + lag(total_assets) OVER w) / 2 END        AS avg_assets,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1
             THEN (equity + lag(equity) OVER w) / 2 END                    AS avg_equity
    FROM core.annual
    WINDOW w AS (PARTITION BY cik ORDER BY fiscal_year_end)
)
SELECT
    filer_name,
    cik,
    fiscal_year,
    round(net_income / revenue, 4)                                          AS net_margin,
    round(revenue / avg_assets, 4)                                          AS asset_turnover,
    round(avg_assets / avg_equity, 4)                                       AS equity_multiplier,
    round(net_income / avg_equity, 4)                                       AS roe,
    round((net_income / revenue) * (revenue / avg_assets) * (avg_assets / avg_equity)
          - net_income / avg_equity, 10)                                    AS identity_residual
FROM avg_bal
WHERE revenue > 0 AND avg_assets > 0 AND avg_equity > 0
QUALIFY row_number() OVER (PARTITION BY cik ORDER BY fiscal_year DESC) = 1
ORDER BY roe DESC
