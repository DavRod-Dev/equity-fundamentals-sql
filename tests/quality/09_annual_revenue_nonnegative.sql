-- Negative revenue is a mapping error for an operating company. It is not
-- one for a commodity fund, an insurer in run-off or a mortgage REIT, whose
-- "Revenues" line legitimately carries investment losses; those sit in
-- SIC 60-69 and are excluded. Small negatives (collaboration-revenue
-- reversals at pre-commercial biotechs) are real too, hence the floor.
SELECT cik, filer_name, sic2, fiscal_year_end, revenue
FROM core.annual
WHERE revenue <= -1e7
  AND sic2 NOT BETWEEN 60 AND 69
