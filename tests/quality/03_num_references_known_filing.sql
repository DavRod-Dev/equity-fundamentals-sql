-- Every numeric value belongs to a filing that is in sub.
SELECT n.adsh, count(*) AS orphan_values
FROM raw.num AS n
LEFT JOIN raw.sub AS s USING (adsh)
WHERE s.adsh IS NULL
GROUP BY n.adsh
