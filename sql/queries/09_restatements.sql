-- Key statement lines whose latest filed value differs from the first reported value, by size of revision.
--
-- The same (filer, concept, period) is reported first in its own 10-K and
-- again as a comparative in the next one; when an amendment or a change in
-- accounting alters it, the two disagree. Small differences are noise from
-- rounding and reclassification, so the filter asks for at least 1 % and
-- $10 million.
SELECT
    f.filer_name,
    v.cik,
    c.concept,
    v.period_end,
    v.qtrs,
    round(v.first_reported_value / 1e6, 1)                                   AS first_reported_mm,
    round(v.value / 1e6, 1)                                                  AS latest_mm,
    round(v.value / nullif(v.first_reported_value, 0) - 1, 3)                AS pct_change,
    v.n_reports,
    v.first_filed,
    v.filed                                                                  AS latest_filed
FROM core.fact_version AS v
JOIN core.concept AS c
  ON c.tag = v.tag AND c.uom = v.uom AND c.period_type = v.period_type
JOIN (
    SELECT cik, arg_max(filer_name, filed) AS filer_name FROM core.filing GROUP BY cik
) AS f USING (cik)
WHERE v.is_latest
  AND v.is_restated
  AND v.qtrs IN (0, 4)
  AND c.uom = 'USD'                        -- share counts have their own scale problems
  AND c.concept <> 'liabilities_and_equity' -- a check line; it restates whenever assets do
  AND abs(v.value - v.first_reported_value) >= 1e7
  AND abs(v.value / nullif(v.first_reported_value, 0) - 1) >= 0.01
ORDER BY abs(v.value - v.first_reported_value) DESC
