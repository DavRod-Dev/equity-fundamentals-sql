-- table
-- Statement line items mapped to the XBRL tags filers actually use.
--
-- Filers are inconsistent and the taxonomy changes: SalesRevenueNet was
-- retired by ASC 606, banks report RevenuesNetOfInterestExpense, some filers
-- use ProfitLoss for net income. Priority resolves a filer reporting several
-- tags for one concept in one period (lower wins). uom says which unit the
-- concept lives in, so share counts never mix with dollars.
SELECT concept, tag, priority, uom, period_type
FROM (VALUES
    ('revenue',              'Revenues',                                                        1, 'USD', 'duration'),
    ('revenue',              'RevenueFromContractWithCustomerExcludingAssessedTax',             2, 'USD', 'duration'),
    ('revenue',              'SalesRevenueNet',                                                 3, 'USD', 'duration'),
    ('revenue',              'SalesRevenueGoodsNet',                                            4, 'USD', 'duration'),
    ('revenue',              'RevenuesNetOfInterestExpense',                                    5, 'USD', 'duration'),
    ('cost_of_revenue',      'CostOfRevenue',                                                   1, 'USD', 'duration'),
    ('cost_of_revenue',      'CostOfGoodsAndServicesSold',                                      2, 'USD', 'duration'),
    ('cost_of_revenue',      'CostOfGoodsSold',                                                 3, 'USD', 'duration'),
    ('gross_profit',         'GrossProfit',                                                     1, 'USD', 'duration'),
    ('operating_income',     'OperatingIncomeLoss',                                             1, 'USD', 'duration'),
    ('pretax_income',        'IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest', 1, 'USD', 'duration'),
    ('pretax_income',        'IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments', 2, 'USD', 'duration'),
    ('income_tax',           'IncomeTaxExpenseBenefit',                                         1, 'USD', 'duration'),
    ('interest_expense',     'InterestExpense',                                                 1, 'USD', 'duration'),
    ('interest_expense',     'InterestExpenseNonoperating',                                     2, 'USD', 'duration'),
    ('net_income',           'NetIncomeLoss',                                                   1, 'USD', 'duration'),
    ('net_income',           'ProfitLoss',                                                      2, 'USD', 'duration'),
    ('depreciation',         'DepreciationDepletionAndAmortization',                            1, 'USD', 'duration'),
    ('depreciation',         'DepreciationAndAmortization',                                     2, 'USD', 'duration'),
    ('operating_cash_flow',  'NetCashProvidedByUsedInOperatingActivities',                      1, 'USD', 'duration'),
    ('capex',                'PaymentsToAcquirePropertyPlantAndEquipment',                      1, 'USD', 'duration'),
    ('capex',                'PaymentsToAcquireProductiveAssets',                               2, 'USD', 'duration'),
    ('total_assets',         'Assets',                                                          1, 'USD', 'instant'),
    ('current_assets',       'AssetsCurrent',                                                   1, 'USD', 'instant'),
    ('current_liabilities',  'LiabilitiesCurrent',                                              1, 'USD', 'instant'),
    ('total_liabilities',    'Liabilities',                                                     1, 'USD', 'instant'),
    ('equity',               'StockholdersEquity',                                              1, 'USD', 'instant'),
    ('equity',               'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest', 2, 'USD', 'instant'),
    ('retained_earnings',    'RetainedEarningsAccumulatedDeficit',                              1, 'USD', 'instant'),
    ('cash',                 'CashAndCashEquivalentsAtCarryingValue',                           1, 'USD', 'instant'),
    ('cash',                 'CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents',   2, 'USD', 'instant'),
    ('long_term_debt',       'LongTermDebtNoncurrent',                                          1, 'USD', 'instant'),
    ('long_term_debt',       'LongTermDebt',                                                    2, 'USD', 'instant'),
    ('shares_outstanding',   'CommonStockSharesOutstanding',                                    1, 'shares', 'instant'),
    ('shares_outstanding',   'EntityCommonStockSharesOutstanding',                              2, 'shares', 'instant'),
    ('diluted_shares',       'WeightedAverageNumberOfDilutedSharesOutstanding',                 1, 'shares', 'duration')
) AS t(concept, tag, priority, uom, period_type)
