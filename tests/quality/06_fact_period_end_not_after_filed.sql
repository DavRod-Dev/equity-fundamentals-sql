-- Reported statement values describe periods that have ended.
SELECT adsh, cik, tag, period_end, filed
FROM core.fact
WHERE period_end > filed
