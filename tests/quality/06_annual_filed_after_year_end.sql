-- An annual statement is filed after the year it describes. (This is not
-- asserted on every fact: declared dividends and similar note items carry
-- future dates legitimately.)
SELECT cik, filer_name, fiscal_year_end, source_filed
FROM core.annual
WHERE source_filed < fiscal_year_end
