import psycopg2

from idfp.config import AppConfiguration


def get_db_conn(config: AppConfiguration):
    return psycopg2.connect(
        database=config.dbname,
        user=config.dbuser,
        password=config.dbpassword,
        host=config.dbhost,
        port=config.dbport,
    )


def get_db_reader_conn(config: AppConfiguration):
    return psycopg2.connect(
        database=config.dbname,
        user=config.dbreaderuser,
        password=config.dbreaderpassword,
        host=config.dbhost,
        port=config.dbport,
    )
