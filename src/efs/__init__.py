"""equity-fundamentals-sql: analytical SQL over SEC Financial Statement Data Sets.

The SEC publishes every XBRL financial statement filed with it as quarterly
bulk files of four tab-separated tables (submissions, numbers, tags,
presentation). This package does the minimum in Python: fetch the zips, load
them into DuckDB, and run SQL files. Everything analytical is in ``sql/``.

    python -m efs load            fetch configured quarters and load raw tables
    python -m efs build           create the core views and tables from sql/models
    python -m efs test            run tests/quality/*.sql assertions
    python -m efs query <name>    run sql/queries/<name>.sql and print a table
    python -m efs list            list available queries with their one-line purpose
"""

__version__ = "0.1.0"
