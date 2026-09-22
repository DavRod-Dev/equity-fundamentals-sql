-- Two things that must hold on every annual balance sheet:
--   1. Total equity (including non-controlling interests) cannot exceed
--      total assets. The parent-only StockholdersEquity can, legitimately:
--      Up-C structures carry negative NCI. Investment companies (SIC 60-69)
--      are skipped; a few closed-end funds tag net assets above total assets.
--   2. Where the filer reports LiabilitiesAndStockholdersEquity, it equals
--      Assets to within 0.1 %: the filer's own statement balances, so a
--      mismatch means the mapped Assets fact is not the balance-sheet total.
-- Assets = liabilities + equity is deliberately NOT asserted. Temporary
-- (mezzanine) equity, redeemable preferred stock and redeemable
-- non-controlling interests sit between the two and are not mapped here;
-- on live data they explain every gap over 10 %.
SELECT cik, filer_name, sic2, fiscal_year_end, total_assets, liabilities_and_equity, equity, equity_total
FROM core.annual
WHERE (equity_total > 0 AND total_assets >= 1e7 AND sic2 NOT BETWEEN 60 AND 69 AND total_assets < equity_total)
   OR (liabilities_and_equity IS NOT NULL AND total_assets > 0
       AND abs(total_assets - liabilities_and_equity) / total_assets > 0.001)
