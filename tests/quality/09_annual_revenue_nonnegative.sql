-- Revenue may be zero (pre-revenue filers) but negative revenue is a mapping error.
SELECT cik, filer_name, fiscal_year_end, revenue
FROM core.annual
WHERE revenue < 0
