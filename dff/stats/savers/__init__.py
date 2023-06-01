from typing import Optional

from .clickhouse import ClickHouseSaver
from .postgresql import PostgresSaver
from .csv_saver import CsvSaver
from .saver import Saver

SAVER_MAPPING = {"csv": CsvSaver, "postgresql": PostgresSaver, "clickhouse": ClickHouseSaver}
"""
Mapping between dbms types and `Saver` classes.
"""


def saver_factory(
    path: str, logs_table: Optional[str] = "otel_logs", traces_table: Optional[str] = "otel_traces"
) -> Saver:
    """
    Use saver_factory to instantiate various saver types.
    The function takes a database connection URI or its equivalent, and a table name.
    The former should be prefixed with database name, followed by the symbol triplet '://'.

    Then, you should list the connection parameters like this: user:password@host:port/database
    The whole URI will then look like this:

    - postgresql://user:pass@host:5430/test
    - clickhouse://user:pass@host:8123/test

    For savers that write to local files, the function expects a file path
    instead of connection parameters:
    csv://file.csv

    :param path: Database uri.
    :param logs_table: Logs table name. Can be set to `None` for csv storage type.
    :param traces_table: Traces table name. Can be set to `None` for csv storage type.
    """
    db_type, _, credentials = path.partition("://")
    if not all((db_type, credentials)):
        raise RuntimeError(f"Incorrect database uri: {path}")
    if db_type not in SAVER_MAPPING:
        raise RuntimeError(
            f"""URI path should be prefixed with one of the following:\n
            {", ".join(SAVER_MAPPING.keys())}.\n
            For more information, see the function doc:\n{saver_factory.__doc__}"""
        )
    saver: Saver = SAVER_MAPPING[db_type](path, logs_table=logs_table, traces_table=traces_table)
    return saver
