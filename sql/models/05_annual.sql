-- table
-- One row per filer per fiscal year: the latest 10-K view of that year.
--
-- FSDS makes the annual selection exact rather than heuristic: sub.period is
-- the balance-sheet date of the filing, so a 10-K own-year figure is the
-- instant at that date or the four-quarter duration ending there. The
-- comparatives a 10-K also carries (period_end one year earlier) become rows
-- of their own, which is how one quarter of data yields several fiscal years.
--
-- Version rule: for each (cik, concept, period_end) take the preferred tag,
-- then the most recently filed 10-K. Tag preference beats recency so a filer
-- reporting both Revenues and RevenueFromContract... gets one consistent
-- series rather than whichever tag happened to be filed last.
WITH annual_facts AS (
    SELECT
        v.cik,
        c.concept,
        c.priority,
        v.period_end,
        v.value,
        v.filed,
        v.adsh
    FROM core.fact_version AS v
    JOIN core.concept AS c
      ON c.tag = v.tag AND c.uom = v.uom AND c.period_type = v.period_type
    WHERE v.is_annual
      AND v.qtrs IN (0, 4)
),
resolved AS (
    SELECT *
    FROM annual_facts
    QUALIFY row_number() OVER (
        PARTITION BY cik, concept, period_end
        ORDER BY priority, filed DESC, adsh DESC
    ) = 1
),
pivoted AS (
    SELECT
        cik,
        period_end                                                          AS fiscal_year_end,
        -- 52/53-week years can end in the first days of January; shifting a
        -- week back labels them with the year they belong to.
        year(period_end - INTERVAL 7 DAY)                                   AS fiscal_year,
        max(CASE WHEN concept = 'revenue'             THEN value END)       AS revenue,
        max(CASE WHEN concept = 'cost_of_revenue'     THEN value END)       AS cost_of_revenue,
        max(CASE WHEN concept = 'gross_profit'        THEN value END)       AS gross_profit_reported,
        max(CASE WHEN concept = 'operating_income'    THEN value END)       AS operating_income,
        max(CASE WHEN concept = 'pretax_income'       THEN value END)       AS pretax_income,
        max(CASE WHEN concept = 'income_tax'          THEN value END)       AS income_tax,
        max(CASE WHEN concept = 'interest_expense'    THEN value END)       AS interest_expense,
        max(CASE WHEN concept = 'net_income'          THEN value END)       AS net_income,
        max(CASE WHEN concept = 'depreciation'        THEN value END)       AS depreciation,
        max(CASE WHEN concept = 'operating_cash_flow' THEN value END)       AS operating_cash_flow,
        max(CASE WHEN concept = 'capex'               THEN value END)       AS capex,
        max(CASE WHEN concept = 'total_assets'        THEN value END)       AS total_assets,
        max(CASE WHEN concept = 'current_assets'      THEN value END)       AS current_assets,
        max(CASE WHEN concept = 'current_liabilities' THEN value END)       AS current_liabilities,
        max(CASE WHEN concept = 'total_liabilities'   THEN value END)       AS total_liabilities_reported,
        max(CASE WHEN concept = 'equity'              THEN value END)       AS equity,
        max(CASE WHEN concept = 'retained_earnings'   THEN value END)       AS retained_earnings,
        max(CASE WHEN concept = 'cash'                THEN value END)       AS cash,
        max(CASE WHEN concept = 'long_term_debt'      THEN value END)       AS long_term_debt,
        max(CASE WHEN concept = 'shares_outstanding'  THEN value END)       AS shares_outstanding,
        max(CASE WHEN concept = 'diluted_shares'      THEN value END)       AS diluted_shares,
        count(*)                                                            AS n_concepts,
        max(filed)                                                          AS source_filed,
        arg_max(adsh, filed)                                                AS source_adsh
    FROM resolved
    GROUP BY cik, period_end
)
SELECT
    p.*,
    -- Derived where the reported line is absent. Many filers report only
    -- LiabilitiesAndStockholdersEquity, so liabilities = assets - equity is
    -- the single most common gap in this data.
    coalesce(p.gross_profit_reported, p.revenue - p.cost_of_revenue)        AS gross_profit,
    coalesce(p.total_liabilities_reported, p.total_assets - p.equity)       AS total_liabilities,
    p.current_assets - p.current_liabilities                                AS working_capital,
    p.operating_cash_flow - p.capex                                         AS free_cash_flow,
    f.filer_name,
    f.sic,
    f.sic2,
    f.filer_status
FROM pivoted AS p
JOIN core.filing AS f ON f.adsh = p.source_adsh
