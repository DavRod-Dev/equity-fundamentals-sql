SELECT cik, fiscal_year_end, count(*) AS n
FROM core.annual
GROUP BY ALL
HAVING count(*) > 1
