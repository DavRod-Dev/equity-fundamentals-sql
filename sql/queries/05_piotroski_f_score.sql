-- Piotroski F-score (0-9) for every filer with two consecutive fiscal years, in pure SQL.
--
-- Nine binary signals, three groups. Each is NULL when its inputs are
-- missing, so the score is only reported when all nine could be evaluated;
-- signals_available says how close the rest came. Averages use the mean of
-- opening and closing balances, as the original paper does.
--
--   Profitability   ROA > 0 | operating cash flow > 0 | ROA improved | OCF > net income (accruals)
--   Leverage        long-term debt / avg assets fell | current ratio rose | no new shares issued
--   Efficiency      gross margin rose | asset turnover rose
WITH yrs AS (
    SELECT
        cik, filer_name, fiscal_year, fiscal_year_end,
        revenue, gross_profit, net_income, operating_cash_flow,
        total_assets, current_assets, current_liabilities, long_term_debt, shares_outstanding,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1 THEN lag(revenue)             OVER w END AS revenue_p,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1 THEN lag(gross_profit)        OVER w END AS gross_profit_p,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1 THEN lag(net_income)          OVER w END AS net_income_p,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1 THEN lag(total_assets)        OVER w END AS total_assets_p,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1 THEN lag(current_assets)      OVER w END AS current_assets_p,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1 THEN lag(current_liabilities) OVER w END AS current_liabilities_p,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1 THEN lag(long_term_debt)      OVER w END AS long_term_debt_p,
        CASE WHEN lag(fiscal_year) OVER w = fiscal_year - 1 THEN lag(shares_outstanding)  OVER w END AS shares_outstanding_p,
        -- ROA in the prior year needs the year before that as its opening balance.
        CASE WHEN lag(fiscal_year, 2) OVER w = fiscal_year - 2 THEN lag(total_assets, 2)  OVER w END AS total_assets_pp
    FROM core.annual
    WINDOW w AS (PARTITION BY cik ORDER BY fiscal_year_end)
),
inputs AS (
    SELECT
        *,
        (total_assets + total_assets_p) / 2                  AS avg_assets,
        (total_assets_p + total_assets_pp) / 2               AS avg_assets_p,
        net_income   / nullif((total_assets + total_assets_p) / 2, 0)      AS roa,
        net_income_p / nullif((total_assets_p + total_assets_pp) / 2, 0)   AS roa_p
    FROM yrs
),
signals AS (
    SELECT
        cik, filer_name, fiscal_year,
        CASE WHEN roa IS NULL THEN NULL WHEN roa > 0 THEN 1 ELSE 0 END                                      AS s_roa_positive,
        CASE WHEN operating_cash_flow IS NULL THEN NULL WHEN operating_cash_flow > 0 THEN 1 ELSE 0 END       AS s_ocf_positive,
        CASE WHEN roa IS NULL OR roa_p IS NULL THEN NULL WHEN roa > roa_p THEN 1 ELSE 0 END                  AS s_roa_improved,
        CASE WHEN operating_cash_flow IS NULL OR net_income IS NULL THEN NULL
             WHEN operating_cash_flow > net_income THEN 1 ELSE 0 END                                         AS s_accruals,
        CASE WHEN avg_assets IS NULL OR avg_assets_p IS NULL OR long_term_debt IS NULL OR long_term_debt_p IS NULL THEN NULL
             WHEN long_term_debt / avg_assets < long_term_debt_p / avg_assets_p THEN 1 ELSE 0 END           AS s_leverage_fell,
        CASE WHEN current_liabilities = 0 OR current_liabilities_p = 0
               OR current_assets IS NULL OR current_assets_p IS NULL
               OR current_liabilities IS NULL OR current_liabilities_p IS NULL THEN NULL
             WHEN current_assets / current_liabilities > current_assets_p / current_liabilities_p THEN 1 ELSE 0 END AS s_liquidity_rose,
        CASE WHEN shares_outstanding IS NULL OR shares_outstanding_p IS NULL THEN NULL
             WHEN shares_outstanding <= shares_outstanding_p THEN 1 ELSE 0 END                               AS s_no_dilution,
        CASE WHEN revenue = 0 OR revenue_p = 0 OR gross_profit IS NULL OR gross_profit_p IS NULL
               OR revenue IS NULL OR revenue_p IS NULL THEN NULL
             WHEN gross_profit / revenue > gross_profit_p / revenue_p THEN 1 ELSE 0 END                      AS s_margin_rose,
        CASE WHEN avg_assets IS NULL OR avg_assets_p IS NULL OR revenue IS NULL OR revenue_p IS NULL THEN NULL
             WHEN revenue / avg_assets > revenue_p / avg_assets_p THEN 1 ELSE 0 END                          AS s_turnover_rose
    FROM inputs
    WHERE total_assets_p IS NOT NULL       -- needs at least the prior year
)
SELECT
    filer_name,
    cik,
    fiscal_year,
    s_roa_positive + s_ocf_positive + s_roa_improved + s_accruals
      + s_leverage_fell + s_liquidity_rose + s_no_dilution
      + s_margin_rose + s_turnover_rose                                        AS f_score,
    (s_roa_positive IS NOT NULL)::INT + (s_ocf_positive IS NOT NULL)::INT + (s_roa_improved IS NOT NULL)::INT
      + (s_accruals IS NOT NULL)::INT + (s_leverage_fell IS NOT NULL)::INT + (s_liquidity_rose IS NOT NULL)::INT
      + (s_no_dilution IS NOT NULL)::INT + (s_margin_rose IS NOT NULL)::INT + (s_turnover_rose IS NOT NULL)::INT AS signals_available,
    s_roa_positive, s_ocf_positive, s_roa_improved, s_accruals,
    s_leverage_fell, s_liquidity_rose, s_no_dilution, s_margin_rose, s_turnover_rose
FROM signals
ORDER BY f_score DESC NULLS LAST, signals_available DESC, filer_name
