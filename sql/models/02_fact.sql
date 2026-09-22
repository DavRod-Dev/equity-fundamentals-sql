-- view
-- Every consolidated numeric value in every kept filing, with its filing context.
--
-- Two filters do most of the work of this repository:
--   coreg IS NULL     the consolidated entity, not a subsidiary or co-registrant
--   segments IS NULL  the total, not a dimensional member (a segment, a
--                     geography, an elimination line). Segment members live in
--                     the same table with the same tag and period; read as
--                     totals they produced a negative gross profit for Walmart
--                     and $638 million of assets for JPMorgan in the first live
--                     run of this code.
-- A 10-K contains prior-period comparatives too, so one filing yields two or
-- three fiscal years of values.
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
  AND n.segments IS NULL
  AND n.value IS NOT NULL
