import csv
import json
import time
import typing as t
import os
from datetime import datetime, timezone

from psycopg2 import sql
from psycopg2._psycopg import connection

from idfp.models import Area
from pydantic import ValidationError


def import_area_csv(
    db_conn: connection,
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
                "area",
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
        with db_conn.cursor() as cur:
            copy_sql = sql.SQL(
                f"COPY {{}}({sql_col_placeholders}) FROM STDIN DELIMITER E{{}} CSV QUOTE {{}}"
            ).format(
                sql.Identifier("area_csv"),
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
                sql.Identifier("area_csv"),
            )
            cur.execute(set_source_id_sql, [source_id])
            set_processed_at_sql = sql.SQL(
                "update {} set processed_at = 0 where source_id = %s"
            ).format(
                sql.Identifier("area_csv"),
            )
            cur.execute(set_processed_at_sql, [source_id])
            db_conn.commit()
    except Exception as exc:
        db_conn.rollback()
        with db_conn.cursor() as cur:
            cur.execute(
                "insert into source_errors(source_id, errors) values(%s, %s)",
                # simple error logging for now
                [source_id, json.dumps({"message": repr(exc)})]
            )
            db_conn.commit()
        raise exc
    return source_id


def process_area_csv_insert(db_conn: connection, source_id: int):
    area_fields = [f.lower() for f in Area.model_fields.keys()]
    area_csv_fields = [*area_fields, "id"]
    area_csv_fields_select = ", ".join(area_csv_fields)
    get_insert_sql = sql.SQL(
        f"select {area_csv_fields_select} from {{}} where source_id = %s and LOWER(IsDeleted) = 'false' and processed_at = 0"
    ).format(sql.Identifier("area_csv"))
    with db_conn.cursor() as cur1, db_conn.cursor() as cur2:
        cur1.execute(get_insert_sql, [source_id])
        while True:
            insert_data = []
            csv_row_ids = []
            rows = cur1.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                csv_row_ids.append(row[len(area_csv_fields) - 1])
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
                        ).format(sql.Identifier("area_csv")),
                        [int(time.time()), err.json(), row[len(area_csv_fields) - 1]],
                    )
                    cur2.execute(
                        "insert into csv_errors(source_id, record_id, errors) values(%s, %s, %s)",
                        [
                            source_id,
                            row[len(area_csv_fields) - 1],
                            err.json(),
                        ],
                    )

            values_placeholder = ", ".join(["%s"] * len(area_fields))
            cur2.executemany(
                sql.SQL(
                    f"insert into {{}}({', '.join(area_fields)}) values({values_placeholder})"
                ).format(sql.Identifier("areas")),
                insert_data,
            )
            cur2.execute(
                sql.SQL("update {} set processed_at = %s where id in %s").format(
                    sql.Identifier("area_csv")
                ),
                [int(time.time()), tuple(csv_row_ids)],
            )
            db_conn.commit()


def process_area_csv_delete(db_conn: connection, source_id: int):
    get_insert_sql = sql.SQL(
        f"select externalidentifier, id from {{}} where source_id = %s and LOWER(IsDeleted) = 'true' and processed_at = 0"
    ).format(sql.Identifier("area_csv"))
    with db_conn.cursor() as cur1, db_conn.cursor() as cur2:
        cur1.execute(get_insert_sql, [source_id])
        while True:
            csv_row_ids: list[int] = []
            rows = cur1.fetchmany(1000)
            if not rows:
                break
            for row in rows:
                cnt = cur2.execute(
                    "delete from areas where externalidentifier=%s",
                    [
                        row[0],
                    ],
                )
                if cur2.rowcount != 0:
                    csv_row_ids.append(row[1])
                else:
                    cur2.execute(
                        "update area_csv set processed_at = %s where id = %s",
                        [
                            int(time.time()),
                            row[1],
                        ],
                    )
                    cur2.execute(
                        "insert into csv_errors(source_id, record_id, errors) values(%s, %s, %s)",
                        [
                            source_id,
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


def process_area_csv(db_conn: connection, source_id: int):
    with db_conn.cursor() as cur:
        cur.execute("update sources set processed_at = now() where id=%s", [source_id])
        db_conn.commit()
    process_area_csv_insert(db_conn, source_id)
    process_area_csv_delete(db_conn, source_id)
