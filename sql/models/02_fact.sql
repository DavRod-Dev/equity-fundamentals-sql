-- view
-- Every consolidated numeric value in every kept filing, with its filing context.
--
-- coreg IS NULL restricts to the consolidated entity: FSDS also carries the
-- same tags for subsidiaries and co-registrants, and summing those with the
-- parent is a classic double-count. A 10-K contains prior-period comparatives
-- too, so one filing yields two or three fiscal years of values.
SELECT
    n.dataset,
    n.adsh,
    f.cik,
    f.form,
    f.is_annual,
    f.filed,
    f.period_end                                       AS filing_period_end,
    f.fiscal_year                                      AS filing_fiscal_year,
    n.tag,
    n.version,
    n.ddate                                            AS period_end,
    n.qtrs,
    CASE WHEN n.qtrs = 0 THEN 'instant' ELSE 'duration' END AS period_type,
    n.uom,
    n.value
FROM raw.num AS n
JOIN core.filing AS f USING (adsh)
WHERE n.coreg IS NULL
  AND n.value IS NOT NULL
