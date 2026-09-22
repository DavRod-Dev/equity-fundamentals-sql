-- Latest fiscal year per filer, key statement lines in $ millions: the base every other query builds on.
SELECT
    filer_name,
    cik,
    sic,
    fiscal_year,
    fiscal_year_end,
    round(revenue             / 1e6, 1) AS revenue_mm,
    round(gross_profit        / 1e6, 1) AS gross_profit_mm,
    round(operating_income    / 1e6, 1) AS operating_income_mm,
    round(net_income          / 1e6, 1) AS net_income_mm,
    round(operating_cash_flow / 1e6, 1) AS ocf_mm,
    round(free_cash_flow      / 1e6, 1) AS fcf_mm,
    round(total_assets        / 1e6, 1) AS assets_mm,
    round(total_liabilities   / 1e6, 1) AS liabilities_mm,
    round(equity              / 1e6, 1) AS equity_mm,
    n_concepts,
    source_filed
FROM core.annual
QUALIFY row_number() OVER (PARTITION BY cik ORDER BY fiscal_year_end DESC) = 1
ORDER BY revenue DESC NULLS LAST
