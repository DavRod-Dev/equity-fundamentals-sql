-- Where each filer sits within its 2-digit SIC industry group and fiscal year: percentile and decile of margin, ROA and FCF margin.
--
-- Peer groups smaller than 20 filers are dropped: a percentile among six
-- companies is noise dressed up as a number. percent_rank runs 0..1 within
-- the group, ntile(10) gives the decile (10 = best), and the group size is
-- carried so a reader can judge how much to trust either.
WITH latest AS (
    SELECT *
    FROM core.annual
    WHERE revenue > 0 AND total_assets > 0
    QUALIFY row_number() OVER (PARTITION BY cik ORDER BY fiscal_year_end DESC) = 1
),
ratios AS (
    SELECT
        cik,
        filer_name,
        sic2,
        fiscal_year,
        net_income     / revenue        AS net_margin,
        net_income     / total_assets   AS roa,
        free_cash_flow / revenue        AS fcf_margin,
        count(*) OVER (PARTITION BY sic2, fiscal_year) AS peers
    FROM latest
)
SELECT
    filer_name,
    cik,
    sic2,
    fiscal_year,
    peers,
    round(net_margin, 3)                                                                   AS net_margin,
    round(percent_rank() OVER (PARTITION BY sic2, fiscal_year ORDER BY net_margin), 3)     AS net_margin_pctile,
    ntile(10)           OVER (PARTITION BY sic2, fiscal_year ORDER BY net_margin)          AS net_margin_decile,
    round(roa, 3)                                                                          AS roa,
    round(percent_rank() OVER (PARTITION BY sic2, fiscal_year ORDER BY roa), 3)            AS roa_pctile,
    round(fcf_margin, 3)                                                                   AS fcf_margin,
    round(percent_rank() OVER (PARTITION BY sic2, fiscal_year ORDER BY fcf_margin), 3)     AS fcf_margin_pctile
FROM ratios
WHERE peers >= 20
ORDER BY sic2, net_margin_pctile DESC, filer_name
