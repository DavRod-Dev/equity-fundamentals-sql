-- Who is in the data: filings, distinct filers and filing-date range by quarter, form and filer status.
--
-- filer_status is SEC's own size class: 1-LAF large accelerated, 2-ACC
-- accelerated, 3-SRA smaller reporting accelerated, 4-NON non-accelerated,
-- 5-SML smaller reporting. Useful for deciding which universe a screen
-- should run over before trusting any percentile.
SELECT
    dataset,
    form,
    filer_status,
    count(*)             AS filings,
    count(DISTINCT cik)  AS filers,
    min(filed)           AS first_filed,
    max(filed)           AS last_filed
FROM core.filing
GROUP BY ALL
ORDER BY dataset, form, filer_status
