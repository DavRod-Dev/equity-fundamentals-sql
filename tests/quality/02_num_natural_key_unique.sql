-- SEC documents (adsh, tag, version, coreg, ddate, qtrs, uom) as the key of num.
SELECT adsh, tag, version, coalesce(coreg, '') AS coreg, ddate, qtrs, uom, count(*) AS n
FROM raw.num
GROUP BY ALL
HAVING count(*) > 1
