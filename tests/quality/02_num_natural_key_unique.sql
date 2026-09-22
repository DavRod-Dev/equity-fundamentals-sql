-- SEC documents (adsh, tag, version, coreg, ddate, qtrs, uom, segments) as
-- the key of num. It holds for consolidated rows. Among dimensional rows the
-- published files themselves contain a few hundred exact duplicates (free-
-- text member names such as counterparties in a derivatives table), which
-- this repository never reads, so the assertion is scoped to what it uses.
SELECT adsh, tag, version, coalesce(coreg, '') AS coreg, ddate, qtrs, uom, count(*) AS n
FROM raw.num
WHERE segments IS NULL
GROUP BY ALL
HAVING count(*) > 1
