-- With positive equity, assets must be at least as large; and where all
-- three reported lines exist, assets = liabilities + equity to within 10 %
-- (the slack is non-controlling interest and temporary equity, which sit
-- outside StockholdersEquity).
SELECT cik, filer_name, fiscal_year_end, total_assets, total_liabilities_reported, equity
FROM core.annual
WHERE (equity > 0 AND total_assets < equity)
   OR (total_liabilities_reported IS NOT NULL AND equity IS NOT NULL AND total_assets > 0
       AND abs(total_assets - total_liabilities_reported - equity) / total_assets > 0.10)
