-- Exactly one version of each fact is flagged latest.
SELECT cik, tag, uom, period_end, qtrs, sum(is_latest::INT) AS n_latest
FROM core.fact_version
GROUP BY ALL
HAVING sum(is_latest::INT) <> 1
