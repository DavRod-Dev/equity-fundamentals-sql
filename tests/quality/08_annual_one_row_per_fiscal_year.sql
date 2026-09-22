-- fiscal_year is a label derived from the year-end date. Two rows per label
-- means a year-end was mislabelled and every LAG-based comparison downstream
-- is silently wrong. The one legitimate cause is a change of fiscal year end
-- (a transition period plus a full year in the same calendar year); filers
-- whose 10-Ks show more than one fye value are excluded for that reason, and
-- the growth queries guard against them separately with a year check.
WITH changed_fye AS (
    SELECT cik
    FROM core.filing
    WHERE is_annual
    GROUP BY cik
    HAVING count(DISTINCT fiscal_year_end_mmdd) > 1
)
SELECT a.cik, a.fiscal_year, count(*) AS n, string_agg(a.fiscal_year_end::VARCHAR, ', ') AS year_ends
FROM core.annual AS a
LEFT JOIN changed_fye USING (cik)
WHERE changed_fye.cik IS NULL
GROUP BY ALL
HAVING count(*) > 1
