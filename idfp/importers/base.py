import csv
import json
import time
import typing as t
import os
from datetime import datetime, timezone

from psycopg2 import sql
from psycopg2._psycopg import connection

from idfp.models import Area
from idfp.definitions import Type, DATA_MAPPING, Source, CSV_ID_FIELD
from pydantic import ValidationError


def import_csv(
    db_conn: connection,
    type: Type,
    csv_fd: t.TextIO,
    *,
    delimiter: str = ",",
    quotechar: t.Optional[str] = None,
):
    if not quotechar:
        quotechar = '"'
    with db_conn.cursor() as cur:
        cur.execute(
            "insert into sources(type, filename, submitted_by, submitted_date, number_of_records) values (%s, %s, %s, %s, %s) returning id",
            [
                type.value,
                os.path.basename(csv_fd.name),
                "",
                datetime.now(timezone.utc).date(),
                0,
            ],
        )
        insert_source_result = cur.fetchone()
        assert insert_source_result is not None
        source_id: int = insert_source_result[0]
        db_conn.commit()

    try:
        reader = csv.reader(csv_fd, delimiter=delimiter, quotechar=quotechar)
        # submitted_by_arr = next(reader)
        # submitted_date_arr = next(reader)
        # nor_arr = next(reader)
        headers = next(reader)
        sql_col_placeholders = ",".join(["{}" for _h in headers])
        sql_cols = [sql.Identifier(h.lower()) for h in headers]
        csv_table_name = DATA_MAPPING[type].csv_table
        with db_conn.cursor() as cur:
            copy_sql = sql.SQL(
                f"COPY {{}}({sql_col_placeholders}) FROM STDIN DELIMITER E{{}} CSV QUOTE {{}}"
            ).format(
                sql.Identifier(csv_table_name),
                *sql_cols,
                sql.Literal(delimiter),
                sql.Literal(quotechar),
            )
            cur.copy_expert(
                copy_sql,
                csv_fd,
            )
            set_source_id_sql = sql.SQL(
                "update {} set source_id = %s where source_id is null"
            ).format(
                sql.Identifier(csv_table_name),
            )
            cur.execute(set_source_id_sql, [source_id])
            set_processed_at_sql = sql.SQL(
                "update {} set processed_at = 0 where source_id = %s"
            ).format(
                sql.Identifier(csv_table_name),
            )
            cur.execute(set_processed_at_sql, [source_id])
            db_conn.commit()
    except Exception as exc:
        db_conn.rollback()
        with db_conn.cursor() as cur:
            cur.execute(
                "insert into source_errors(source_id, errors) values(%s, %s)",
                # simple error logging for now
                [source_id, json.dumps({"message": repr(exc)})],
            )
            db_conn.commit()
        raise exc
    return source_id


def process_csv_insert(db_conn: connection, source: Source):
    model = DATA_MAPPING[source.type].model
    csv_table_name = DATA_MAPPING[source.type].csv_table

    fields = [f.lower() for f in model.model_fields.keys()]
    csv_fields = [*fields, CSV_ID_FIELD]
    csv_fields_select = ", ".join(csv_fields)
    get_insert_sql = sql.SQL(
        f"select {csv_fields_select} from {{}} where source_id = %s and LOWER(IsDeleted) = 'false' and processed_at = 0"
    ).format(sql.Identifier(csv_table_name))
    with db_conn.cursor() as cur1, db_conn.cursor() as cur2:
        cur1.execute(get_insert_sql, [source.id])
        while True:
            insert_data = []
            csv_row_ids = []
            rows = cur1.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                csv_row_ids.append(row[len(csv_fields) - 1])
                fields_values = {
                    f: row[i] for (i, f) in enumerate(Area.model_fields.keys())
                }
                try:
                    _ = Area(**fields_values)
                    # TODO: check if ExternalIdentifier exists
                    insert_data.append(list(fields_values.values()))
                except ValidationError as err:
                    cur2.execute(
                        sql.SQL(
                            "update {} set processed_at = %s and errors = %s where id = %s"
                        ).format(sql.Identifier(csv_table_name)),
                        [int(time.time()), err.json(), row[len(csv_fields) - 1]],
                    )
                    cur2.execute(
                        "insert into csv_errors(source_id, record_id, errors) values(%s, %s, %s)",
                        [
                            source.id,
                            row[len(csv_fields) - 1],
                            err.json(),
                        ],
                    )

            values_placeholder = ", ".join(["%s"] * len(fields))
            cur2.executemany(
                sql.SQL(
                    f"insert into {{}}({', '.join(fields)}) values({values_placeholder})"
                ).format(sql.Identifier("areas")),
                insert_data,
            )
            cur2.execute(
                sql.SQL("update {} set processed_at = %s where id in %s").format(
                    sql.Identifier(csv_table_name)
                ),
                [int(time.time()), tuple(csv_row_ids)],
            )
            db_conn.commit()


def process_csv_delete(db_conn: connection, source: Source):
    table = DATA_MAPPING[source.type].table
    csv_table_name = DATA_MAPPING[source.type].csv_table
    fields = [DATA_MAPPING[source.type].primary_key, CSV_ID_FIELD]
    fields_select = ", ".join(fields)
    get_insert_sql = sql.SQL(
        f"select {fields_select} from {{}} where source_id = %s and LOWER(IsDeleted) = 'true' and processed_at = 0"
    ).format(sql.Identifier(csv_table_name))
    with db_conn.cursor() as cur1, db_conn.cursor() as cur2:
        cur1.execute(get_insert_sql, [source.id])
        while True:
            csv_row_ids: list[int] = []
            rows = cur1.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                cur2.execute(
                    sql.SQL("delete from {} where {}=%s").format(
                        sql.Identifier(table), sql.Identifier(fields[0])
                    ),
                    [
                        row[0],
                    ],
                )
                if cur2.rowcount != 0:
                    csv_row_ids.append(row[1])
                else:
                    cur2.execute(
                        sql.SQL("update {} set processed_at = %s where id = %s").format(sql.Identifier(csv_table_name)),
                        [
                            int(time.time()),
                            row[1],
                        ],
                    )
                    cur2.execute(
                        "insert into csv_errors(source_id, record_id, errors) values(%s, %s, %s)",
                        [
                            source.id,
                            row[1],
                            json.dumps(
                                {"message": "ExternalIdentifier does not exist"}
                            ),
                        ],
                    )
            if csv_row_ids:
                cur2.execute(
                    "update area_csv set processed_at = %s where id in %s",
                    [int(time.time()), tuple(csv_row_ids)],
                )
            db_conn.commit()


def process_csv(db_conn: connection, source: Source):
    with db_conn.cursor() as cur:
        cur.execute("update sources set processed_at = now() where id=%s", [source.id])
        db_conn.commit()
    process_csv_insert(db_conn, source)
    process_csv_delete(db_conn, source)


def import_and_process_csv(
    *,
    db_conn: connection,
    type: Type,
    csv_fo: t.TextIO,
    delimiter: str = ",",
    quotechar: str = '"',
):
    source_id = import_csv(
        db_conn, type, csv_fo, delimiter=delimiter, quotechar=quotechar
    )
    source = Source(id=source_id, type=type)
    process_csv(db_conn, source)
