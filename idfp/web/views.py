import csv
import io
import logging
import os

from flask import render_template, current_app, request, send_file, abort
from psycopg2 import sql

from idfp.config import AppConfiguration
from idfp.db import get_db_conn, get_db_reader_conn
from idfp.definitions import Type, DATA_MAPPING

logger = logging.getLogger(__name__)


def index_view():
    logger.info("hello from idfp")
    if request.args.get("test-debugger"):
        raise ValueError("testing")
    return render_template("index.html")


def sources_views():
    config: AppConfiguration = current_app.config["config"]

    with get_db_conn(config) as db_conn:
        with db_conn.cursor() as cur:
            sources = cur.execute(
                """select
                    sources.id,
                    type,
                    filename,
                    submitted_date,
                    processed_at,
                    errors as source_errors,
                    exists(select csv_errors.id from csv_errors where csv_errors.source_id=sources.id) as csv_errors
                from sources
                left join source_errors
                on sources.id = source_errors.source_id
                order by sources.id desc"""
            )

            headers = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
    return render_template("sources.j2", headers=headers, rows=rows)


def csv_errors_download():
    config: AppConfiguration = current_app.config["config"]

    csv_data = io.StringIO()
    csv_writer = csv.writer(csv_data)

    try:
        source_id = int(request.args.get("source_id"))
    except Exception:
        return abort(404)

    with get_db_conn(config) as db_conn:
        with db_conn.cursor() as cur:
            cur.execute("select type, filename from sources where id = %s", [source_id])
            row = cur.fetchone()
            source_type = Type(row[0])
            filename = os.path.splitext(row[1])[0] + '_errors.csv'
            csv_table_name = DATA_MAPPING[source_type].csv_table
            model = DATA_MAPPING[source_type].model
            fields = [f.lower() for f in model.model_fields.keys()]+['isdeleted']
            fields_select_sql = ", ".join(fields)
            cur.execute(
                sql.SQL(
                    f"""select
                    {fields_select_sql},
                    csv_errors.errors
                    from {{}} t
                    join csv_errors
                    on t.id = csv_errors.record_id
                    where csv_errors.source_id=%s"""
                ).format(sql.Identifier(csv_table_name)),
                [source_id],
            )
            headers = [desc[0] for desc in cur.description]
            csv_writer.writerow(headers)
            rows = cur.fetchall()
            for row in rows:
                csv_writer.writerow(row)
    csv_data.seek(0)
    return send_file(
        io.BytesIO(csv_data.read().encode()),
        "application/csv",
        True,
        filename,
    )


def query_view():
    config: AppConfiguration = current_app.config["config"]
    error = None
    rows = []
    headers = []
    sql = ""
    if request.method == "POST" and request.form.get("sql"):
        sql = request.form.get("sql")
        assert sql is not None
        with get_db_reader_conn(config) as db_conn:
            with db_conn.cursor() as cur:
                try:
                    cur.execute(sql)
                    headers = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()
                except Exception as e:
                    error = str(e)

    return render_template("sql.j2", headers=headers, rows=rows, error=error, sql=sql)
