-- A filing cannot be submitted before its balance-sheet date.
SELECT adsh, cik, form, period_end, filed
FROM core.filing
WHERE period_end > filed
