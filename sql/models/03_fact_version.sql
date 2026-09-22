-- table
-- Every version of every fact, ranked so a query can choose deliberately.
--
-- Natural key of a fact: (cik, tag, uom, period_end, qtrs). The same key is
-- reported by the original filing, by later filings as a comparative, and by
-- any amendment. version_rank = 1 is the most recently filed report; the
-- first-filed value is carried alongside so restatements are one comparison.
SELECT
    *,
    version_rank = 1                     AS is_latest,
    value <> first_reported_value        AS is_restated
FROM (
    SELECT
        *,
        row_number()       OVER w_desc AS version_rank,
        count(*)           OVER w_all  AS n_reports,
        min(filed)         OVER w_all  AS first_filed,
        first_value(value) OVER w_asc  AS first_reported_value
    FROM core.fact
    WINDOW
        w_all  AS (PARTITION BY cik, tag, uom, period_end, qtrs),
        w_desc AS (PARTITION BY cik, tag, uom, period_end, qtrs ORDER BY filed DESC, adsh DESC),
        w_asc  AS (PARTITION BY cik, tag, uom, period_end, qtrs ORDER BY filed ASC, adsh ASC
                   ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
)
