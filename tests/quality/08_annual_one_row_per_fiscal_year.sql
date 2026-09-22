-- fiscal_year is a label derived from the year-end date. Two rows per
-- label means a 52/53-week year-end was mislabelled and every LAG-based
-- comparison downstream is silently wrong.
SELECT cik, fiscal_year, count(*) AS n, string_agg(fiscal_year_end::VARCHAR, ', ') AS year_ends
FROM core.annual
GROUP BY ALL
HAVING count(*) > 1
