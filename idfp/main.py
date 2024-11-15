import logging
import click
import typing as t

from idfp.db import get_db_conn
from idfp.definitions import Type
from idfp.config import AppConfiguration, configure

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


@click.group()
@click.option("--config", "-c", "config_fo", required=True, type=click.File('rb'))
@click.pass_context
def cli(ctx: click.Context, config_fo: t.BinaryIO):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)
    logger.info(f"Loading configuration from {config_fo.name}")
    config = configure(config_fo)
    ctx.obj['config'] = config


@cli.command()
@click.argument("fp")
@click.option("--delimiter", default=",", type=str)
@click.option("--quotechar", default='"', type=str)
@click.pass_context
def import_area_csv(ctx: click.Context, fp: str, delimiter: str, quotechar: str):
    from idfp.importers.area import (
        import_area_csv as _import_area_csv,
        process_area_csv,
    )

    with get_db_conn(ctx.obj['config']) as db_conn, open(fp) as csv_fo:
        try:
            source_id = _import_area_csv(db_conn, csv_fo, delimiter=delimiter, quotechar=quotechar)
            process_area_csv(db_conn, source_id)
        except Exception as exc:
            db_conn.rollback()
            raise exc


@cli.command()
@click.argument("file", type=click.File('r'))
@click.argument("type_str", metavar='TYPE')
@click.option("--delimiter", default=",", type=str)
@click.option("--quotechar", default='"', type=str)
@click.pass_context
def import_csv(
    ctx: click.Context, file: t.TextIO, type_str: str, delimiter: str, quotechar: str
):
    from idfp.importers import importers

    type = Type(type_str)
    importer = importers[type]

    with get_db_conn(ctx.obj["config"]) as db_conn:
        try:
            importer(
                db_conn=db_conn, csv_fo=file, delimiter=delimiter, quotechar=quotechar
            )
        except Exception as exc:
            db_conn.rollback()
            raise exc


@cli.command()
@click.pass_context
def web(ctx: click.Context):
    """Run gunicorn webserver under the hood"""
    import importlib
    import sys
    from gunicorn.app.wsgiapp import WSGIApplication
    from idfp.web import create_app

    config: AppConfiguration = ctx.obj["config"]

    # use factory to make gunicorn reload work
    # ps: the reloading file patterns is hard to use,
    # so just use watchmedo or watchman instead
    def app_factory():
        app = create_app(ctx.obj['config'])
        return app
    web_module = importlib.import_module("idfp.web")
    web_module.app_factory = app_factory

    gunicorn_cfg = importlib.import_module("idfp.web.gunicorn")
    gunicorn_cfg.bind = config.web_bind
    gunicorn_cfg.preload_app = config.web_preload
    if config.web_workers:
        gunicorn_cfg.workers = config.web_workers
    gunicorn_cfg.reuse_port = config.web_reuse_port

    # save and restore `sys.argv` to make USR2 handling work
    old_sys_argv = sys.argv[:]
    sys.argv = sys.argv[:1] + ["-c", "python:idfp.web.gunicorn"]
    gunicorn_server = WSGIApplication(prog='idfp')
    sys.argv = old_sys_argv
    gunicorn_server.run()


if __name__ == "__main__":
    cli()
