"""Build synthetic SEC Financial Statement Data Set archives in the exact
published layout: a zip per quarter holding tab-separated sub, num, tag and
pre files with the SEC column headers.

Three filers, chosen so every query has something to find and every number
can be checked by hand (see EXPECTED at the bottom):

  Alpha Widgets   industrial, Dec year end, two 10-Ks and three 10-Qs;
                  one comparative restated; earns a Piotroski 8 of 9
  Beta Bank       financial (excluded from Altman), reports revenue under
                  RevenuesNetOfInterestExpense and no Liabilities line
                  (exercises tag priority and the derived-liabilities rule);
                  carries a co-registrant row that must be ignored
  Gamma Retail    52/53-week year ending 4 Jan 2025, loss-making, in the
                  Altman distress zone

Amounts are written in dollars (millions * 1e6) so the restatement query
thresholds, which are in real money, apply.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

SUB_COLS = ("adsh cik name sic countryba stprba cityba zipba bas1 bas2 baph countryma stprma cityba2 "
            "zipma mas1 mas2 countryinc stprinc ein former changed afs wksi fye form period fy fp filed "
            "prevrpt detail instance nciks aciks").split()
SUB_COLS[SUB_COLS.index("cityba2")] = "cityma"
NUM_COLS = "adsh tag version coreg ddate qtrs uom value footnote".split()
TAG_COLS = "tag version custom abstract datatype iord crdr tlabel doc".split()
PRE_COLS = "adsh report line stmt inpth rfile tag version plabel negating".split()

V = "us-gaap/2024"
M = 1_000_000

ALPHA, BETA, GAMMA = 1000001, 1000002, 1000003
A23 = "0001000001-24-000001"   # Alpha 10-K FY2023
A24 = "0001000001-25-000001"   # Alpha 10-K FY2024
AQ1, AQ2, AQ3 = "0001000001-24-000011", "0001000001-24-000012", "0001000001-24-000013"
A8K = "0001000001-25-000009"
B24 = "0001000002-25-000001"
G24 = "0001000003-25-000001"

INSTANT = {"Assets", "AssetsCurrent", "LiabilitiesCurrent", "Liabilities", "StockholdersEquity",
           "RetainedEarningsAccumulatedDeficit", "LongTermDebtNoncurrent", "CommonStockSharesOutstanding",
           "CashAndCashEquivalentsAtCarryingValue"}


def sub_row(adsh, cik, name, sic, form, period, fy, fp, filed, fye="1231"):
    r = dict.fromkeys(SUB_COLS, "")
    r.update(adsh=adsh, cik=cik, name=name, sic=sic, countryba="US", stprba="NY", cityba="NEW YORK",
             countryinc="US", afs="1-LAF", wksi=0, fye=fye, form=form, period=period, fy=fy, fp=fp,
             filed=filed, prevrpt=0, detail=1, instance=f"{adsh}.xml", nciks=1)
    return r


def facts(adsh, ddate, values, *, qtrs=None, coreg=""):
    """values: {tag: millions}. qtrs defaults to 4 for durations, 0 for instants."""
    out = []
    for tag, mm in values.items():
        q = 0 if tag in INSTANT else (4 if qtrs is None else qtrs)
        uom = "shares" if tag == "CommonStockSharesOutstanding" else "USD"
        out.append(dict(adsh=adsh, tag=tag, version=V, coreg=coreg, ddate=ddate, qtrs=q, uom=uom,
                        value=int(mm * M), footnote=""))
    return out


# Alpha statements by fiscal year, in $ millions.
ALPHA_FY = {
    2022: dict(Revenues=900, CostOfRevenue=600, OperatingIncomeLoss=90, NetIncomeLoss=60,
               NetCashProvidedByUsedInOperatingActivities=90, PaymentsToAcquirePropertyPlantAndEquipment=30,
               Assets=800, AssetsCurrent=300, LiabilitiesCurrent=150, Liabilities=300, StockholdersEquity=500,
               RetainedEarningsAccumulatedDeficit=220, LongTermDebtNoncurrent=100, CommonStockSharesOutstanding=100),
    2023: dict(Revenues=1000, CostOfRevenue=650, OperatingIncomeLoss=110, NetIncomeLoss=80,
               NetCashProvidedByUsedInOperatingActivities=100, PaymentsToAcquirePropertyPlantAndEquipment=40,
               Assets=1000, AssetsCurrent=400, LiabilitiesCurrent=200, Liabilities=400, StockholdersEquity=600,
               RetainedEarningsAccumulatedDeficit=300, LongTermDebtNoncurrent=150, CommonStockSharesOutstanding=100),
    2024: dict(Revenues=1210, CostOfRevenue=760, OperatingIncomeLoss=160, NetIncomeLoss=120,
               NetCashProvidedByUsedInOperatingActivities=170, PaymentsToAcquirePropertyPlantAndEquipment=40,
               Assets=1200, AssetsCurrent=500, LiabilitiesCurrent=220, Liabilities=450, StockholdersEquity=750,
               RetainedEarningsAccumulatedDeficit=400, LongTermDebtNoncurrent=140, CommonStockSharesOutstanding=100),
}
ALPHA_2023_RESTATED = dict(ALPHA_FY[2023], NetCashProvidedByUsedInOperatingActivities=120)  # in the FY2024 10-K

BETA_2024 = dict(RevenuesNetOfInterestExpense=500, NetIncomeLoss=50, Assets=5000, StockholdersEquity=400,
                 NetCashProvidedByUsedInOperatingActivities=70, RetainedEarningsAccumulatedDeficit=250)
GAMMA_2024 = dict(Revenues=2000, CostOfRevenue=1500, OperatingIncomeLoss=-10, NetIncomeLoss=-20,
                  NetCashProvidedByUsedInOperatingActivities=5, PaymentsToAcquirePropertyPlantAndEquipment=15,
                  Assets=900, AssetsCurrent=400, LiabilitiesCurrent=350, Liabilities=600, StockholdersEquity=300,
                  RetainedEarningsAccumulatedDeficit=-50, LongTermDebtNoncurrent=300, CommonStockSharesOutstanding=50)


def dataset_2024q1():
    subs = [sub_row(A23, ALPHA, "ALPHA WIDGETS INC", 3570, "10-K", "20231231", 2023, "FY", "20240220")]
    nums = facts(A23, "20231231", ALPHA_FY[2023]) + facts(A23, "20221231", ALPHA_FY[2022])
    return subs, nums


def dataset_2025q1():
    subs = [
        sub_row(A24, ALPHA, "ALPHA WIDGETS INC", 3570, "10-K", "20241231", 2024, "FY", "20250220"),
        sub_row(AQ1, ALPHA, "ALPHA WIDGETS INC", 3570, "10-Q", "20240331", 2024, "Q1", "20240505"),
        sub_row(AQ2, ALPHA, "ALPHA WIDGETS INC", 3570, "10-Q", "20240630", 2024, "Q2", "20240805"),
        sub_row(AQ3, ALPHA, "ALPHA WIDGETS INC", 3570, "10-Q", "20240930", 2024, "Q3", "20241105"),
        sub_row(A8K, ALPHA, "ALPHA WIDGETS INC", 3570, "8-K", "20241231", 2024, "FY", "20250115"),
        sub_row(B24, BETA, "BETA BANK CORP", 6022, "10-K", "20241231", 2024, "FY", "20250301"),
        sub_row(G24, GAMMA, "GAMMA RETAIL INC", 5311, "10-K", "20250104", 2024, "FY", "20250310", fye="0104"),
    ]
    nums = (
        facts(A24, "20241231", ALPHA_FY[2024]) + facts(A24, "20231231", ALPHA_2023_RESTATED)
        # 10-Qs: the quarter itself (qtrs=1) and year-to-date (qtrs=n)
        + facts(AQ1, "20240331", {"Revenues": 250}, qtrs=1)
        + facts(AQ2, "20240630", {"Revenues": 300}, qtrs=1) + facts(AQ2, "20240630", {"Revenues": 550}, qtrs=2)
        + facts(AQ3, "20240930", {"Revenues": 350}, qtrs=1) + facts(AQ3, "20240930", {"Revenues": 900}, qtrs=3)
        # 8-K exhibit repeating the annual figure; must be excluded upstream
        + facts(A8K, "20241231", {"Revenues": 1210})
        + facts(B24, "20241231", BETA_2024)
        + facts(B24, "20241231", {"Assets": 999_999}, coreg="BETA SUBSIDIARY LLC")
        + facts(G24, "20250104", GAMMA_2024)
    )
    return subs, nums


def tag_rows(nums):
    seen = {}
    for n in nums:
        seen.setdefault((n["tag"], n["version"]), dict(
            tag=n["tag"], version=n["version"], custom=0, abstract=0,
            datatype="shares" if n["uom"] == "shares" else "monetary",
            iord="I" if n["qtrs"] == 0 else "D",
            crdr="C" if "Liabilit" in n["tag"] or "Equity" in n["tag"] else "D",
            tlabel=n["tag"], doc=""))
    return list(seen.values())


def pre_rows(nums):
    out, line = [], {}
    for n in nums:
        key = (n["adsh"], n["tag"])
        if key in line:
            continue
        line[key] = len(line) + 1
        stmt = "BS" if n["qtrs"] == 0 else ("CF" if "Cash" in n["tag"] or "Payments" in n["tag"] else "IS")
        out.append(dict(adsh=n["adsh"], report=1, line=line[key], stmt=stmt, inpth=0, rfile="H",
                        tag=n["tag"], version=n["version"], plabel=n["tag"], negating=0))
    return out


def _tsv(cols, rows):
    lines = ["\t".join(cols)]
    for r in rows:
        lines.append("\t".join("" if r.get(c) is None else str(r.get(c, "")) for c in cols))
    return ("\n".join(lines) + "\n").encode("utf-8")


def build(target_dir: Path) -> list[Path]:
    """Write 2024q1.zip and 2025q1.zip into target_dir; returns their paths."""
    target_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for quarter, (subs, nums) in (("2024q1", dataset_2024q1()), ("2025q1", dataset_2025q1())):
        path = target_dir / f"{quarter}.zip"
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("sub.txt", _tsv(SUB_COLS, subs))
            zf.writestr("num.txt", _tsv(NUM_COLS, nums))
            zf.writestr("tag.txt", _tsv(TAG_COLS, tag_rows(nums)))
            zf.writestr("pre.txt", _tsv(PRE_COLS, pre_rows(nums)))
            zf.writestr("readme.htm", b"<html>synthetic fixture</html>")
        paths.append(path)
    return paths


# Hand-computed expectations for Alpha fiscal 2024 (see the docstring of each query).
EXPECTED = dict(
    alpha_2024_avg_assets=1100 * M,
    alpha_2024_roa=120 / 1100,
    alpha_2023_roa=80 / 900,
    alpha_piotroski=8,             # asset turnover fell (1.100 vs 1.111); everything else passes
    alpha_z=6.56 * (280 / 1200) + 3.26 * (400 / 1200) + 6.72 * (160 / 1200) + 1.05 * (750 / 450),
    gamma_z=6.56 * (50 / 900) + 3.26 * (-50 / 900) + 6.72 * (-10 / 900) + 1.05 * (300 / 600),
    alpha_roe=120 / 675,
    alpha_revenue_growth=1210 / 1000 - 1,
    alpha_quarters=(250, 300, 350, 310),
    beta_liabilities=4600 * M,
)
