"""Load a Financial Statement Data Set archive into DuckDB.

Each archive holds four tab-separated files. They are extracted untouched to
``data/staging/<quarter>/`` and read with DuckDB's CSV reader, all columns as
text, then cast on insert. That keeps the on-disk landing zone byte-identical
to what SEC published and puts every type decision in one visible place.

Loading is idempotent per quarter: rows tagged with that ``dataset`` are
replaced, not appended. Columns are selected by name, so a file with extra
columns (SEC has added some over the years) loads without changes.

One column that must not be ignored: ``segments``. Since 2020 the data sets
carry dimensional facts (revenue by segment, assets by geography,
eliminations) in the same table as the consolidated totals, distinguished
only by a non-empty segments value. Read them as totals and every
aggregate downstream is wrong.
"""
from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from efs import config

RAW_DDL = """
CREATE SCHEMA IF NOT EXISTS raw;

-- One row per submission (filing).
CREATE TABLE IF NOT EXISTS raw.sub (
    dataset     VARCHAR NOT NULL,
    adsh        VARCHAR NOT NULL,   -- accession number, the filing's key
    cik         BIGINT  NOT NULL,
    name        VARCHAR,
    sic         INTEGER,
    countryba   VARCHAR,
    stprba      VARCHAR,
    cityba      VARCHAR,
    countryinc  VARCHAR,
    ein         VARCHAR,
    afs         VARCHAR,            -- filer status: 1-LAF, 2-ACC, 3-SRA, 4-NON, 5-SML
    wksi        INTEGER,
    fye         VARCHAR,            -- fiscal year end, MMDD
    form        VARCHAR NOT NULL,
    period      DATE,               -- balance sheet date of the filing
    fy          INTEGER,
    fp          VARCHAR,
    filed       DATE    NOT NULL,
    prevrpt     BOOLEAN,            -- superseded by a later amendment
    detail      BOOLEAN,
    instance    VARCHAR,
    nciks       INTEGER,
    aciks       VARCHAR
);

-- One row per numeric value in a filing.
CREATE TABLE IF NOT EXISTS raw.num (
    dataset   VARCHAR NOT NULL,
    adsh      VARCHAR NOT NULL,
    tag       VARCHAR NOT NULL,
    version   VARCHAR NOT NULL,     -- taxonomy (us-gaap/2024) or the adsh for custom tags
    coreg     VARCHAR,              -- co-registrant; NULL means the consolidated entity
    segments  VARCHAR,              -- dimensional qualifiers; NULL means the total, not a member
    ddate     DATE    NOT NULL,     -- period end
    qtrs      INTEGER NOT NULL,     -- 0 = instant, else duration in quarters
    uom       VARCHAR NOT NULL,
    value     DOUBLE,
    footnote  VARCHAR
);

-- Tag definitions. The same (tag, version) recurs in every quarter's file.
CREATE TABLE IF NOT EXISTS raw.tag (
    dataset   VARCHAR NOT NULL,
    tag       VARCHAR NOT NULL,
    version   VARCHAR NOT NULL,
    custom    BOOLEAN,
    abstract  BOOLEAN,
    datatype  VARCHAR,
    iord      VARCHAR,              -- I = instant, D = duration
    crdr      VARCHAR,              -- natural balance: C or D
    tlabel    VARCHAR,
    doc       VARCHAR
);

-- Where each tag sits in the filer's own statements.
CREATE TABLE IF NOT EXISTS raw.pre (
    dataset   VARCHAR NOT NULL,
    adsh      VARCHAR NOT NULL,
    report    INTEGER,
    line      INTEGER,
    stmt      VARCHAR,              -- BS, IS, CF, EQ, CI, SI, UN
    inpth     BOOLEAN,
    rfile     VARCHAR,
    tag       VARCHAR NOT NULL,
    version   VARCHAR NOT NULL,
    plabel    VARCHAR,
    negating  BOOLEAN
);

CREATE TABLE IF NOT EXISTS raw.load_log (
    dataset    VARCHAR   NOT NULL,
    "table"    VARCHAR   NOT NULL,
    row_count  BIGINT    NOT NULL,
    loaded_at  TIMESTAMP NOT NULL
);
"""

# Typed projection of each file. Everything arrives as text; TRY_CAST turns
# the odd malformed value into NULL instead of aborting a 3-million-row load.
_SELECTS = {
    "sub": """
        ? AS dataset, adsh, TRY_CAST(cik AS BIGINT), name, TRY_CAST(sic AS INTEGER),
        countryba, stprba, cityba, countryinc, ein, afs, TRY_CAST(wksi AS INTEGER), fye, form,
        TRY_STRPTIME(period, '%Y%m%d')::DATE, TRY_CAST(fy AS INTEGER), fp,
        TRY_STRPTIME(filed, '%Y%m%d')::DATE,
        TRY_CAST(prevrpt AS INTEGER) = 1, TRY_CAST(detail AS INTEGER) = 1,
        instance, TRY_CAST(nciks AS INTEGER), aciks
    """,
    "num": """
        ? AS dataset, adsh, tag, version, nullif(coreg, ''), nullif(segments, ''),
        TRY_STRPTIME(ddate, '%Y%m%d')::DATE, TRY_CAST(qtrs AS INTEGER), uom,
        TRY_CAST(value AS DOUBLE), nullif(footnote, '')
    """,
    "tag": """
        ? AS dataset, tag, version, TRY_CAST(custom AS INTEGER) = 1, TRY_CAST(abstract AS INTEGER) = 1,
        datatype, iord, crdr, tlabel, doc
    """,
    "pre": """
        ? AS dataset, adsh, TRY_CAST(report AS INTEGER), TRY_CAST(line AS INTEGER), stmt,
        TRY_CAST(inpth AS INTEGER) = 1, rfile, tag, version, plabel, TRY_CAST(negating AS INTEGER) = 1
    """,
}


class SchemaError(RuntimeError):
    """The database on disk was created by an older version of this loader."""


def ensure_raw_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(RAW_DDL)
    # CREATE TABLE IF NOT EXISTS never alters an existing table. Rather than
    # migrate in place, say so: the data is reproducible from cached archives.
    cols = {r[0] for r in con.execute("SELECT column_name FROM information_schema.columns "
                                      "WHERE table_schema = 'raw' AND table_name = 'num'").fetchall()}
    if "segments" not in cols:
        raise SchemaError(
            "raw.num was created without the segments column by an earlier version. "
            "Delete the database file and run `python -m efs load` again; archives in data/raw are reused."
        )


def extract(archive: Path, staging_dir: Path = config.STAGING_DIR) -> dict[str, Path]:
    """Unzip the four tables for one quarter; returns table -> file path."""
    quarter = archive.stem
    target = staging_dir / quarter
    target.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    with zipfile.ZipFile(archive) as zf:
        for table in config.TABLES:
            member = f"{table}.txt"
            if member not in zf.namelist():
                raise FileNotFoundError(f"{archive.name} has no {member}")
            zf.extract(member, target)
            out[table] = target / member
    return out


def _read_csv_expr(path: Path) -> str:
    # SEC files: tab-delimited, header row, no quoting at all (names may contain
    # quote characters), UTF-8 with the occasional stray byte.
    literal = path.as_posix().replace("'", "''")
    return (
        f"read_csv('{literal}', delim='\t', header=true, all_varchar=true, "
        f"quote='', escape='', null_padding=true, ignore_errors=true, encoding='utf-8')"
    )


def load_quarter(con: duckdb.DuckDBPyConnection, quarter: str, files: dict[str, Path], log=print) -> dict[str, int]:
    """Replace one quarter's rows in every raw table. One transaction; all or nothing."""
    counts: dict[str, int] = {}
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    con.execute("BEGIN")
    try:
        for table in config.TABLES:
            con.execute(f"DELETE FROM raw.{table} WHERE dataset = ?", [quarter])
            con.execute(f"DELETE FROM raw.load_log WHERE dataset = ? AND \"table\" = ?", [quarter, table])
            con.execute(
                f"INSERT INTO raw.{table} SELECT {_SELECTS[table]} FROM {_read_csv_expr(files[table])}",
                [quarter],
            )
            n = con.execute(f"SELECT count(*) FROM raw.{table} WHERE dataset = ?", [quarter]).fetchone()[0]
            con.execute("INSERT INTO raw.load_log VALUES (?, ?, ?, ?)", [quarter, table, n, now])
            counts[table] = n
            log(f"[load]  {quarter} raw.{table:<4} {n:>12,} rows")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return counts
