-- Statement codes are a closed set in the SEC specification.
SELECT stmt, count(*) AS n
FROM raw.pre
WHERE stmt NOT IN ('BS', 'IS', 'CF', 'EQ', 'CI', 'SI', 'UN', 'CP')
GROUP BY stmt
