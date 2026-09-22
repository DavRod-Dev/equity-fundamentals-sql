-- An accession number identifies exactly one filing, across every loaded quarter.
SELECT adsh, count(*) AS n, string_agg(dataset, ', ') AS datasets
FROM raw.sub
GROUP BY adsh
HAVING count(*) > 1
