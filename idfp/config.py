import logging.config
import pathlib
import typing as t
import secrets
from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass
class AppConfiguration:
    secret_key: str
    logconfig_fp: str
    debug: bool
    dbname: str = "idfp"
    dbhost: t.Optional[str] = None
    dbport: t.Optional[int] = None
    dbuser: str = "postgres"
    dbpassword: t.Optional[str] = None
    web_autoreload: bool = False
    web_bind: list[str] = Field(default_factory=lambda: ["localhost:8000"])


class AppF(BaseModel):
    secret_key: str = Field(default_factory=secrets.token_hex)
    dbname: str = 'idfp'
    dbhost: t.Optional[str] = None
    dbport: t.Optional[int] = None
    dbuser: str = 'postgres'
    dbpassword: t.Optional[str] = None
    debug: bool = False
    logconfig_fp: t.Optional[str] = None
    web_autoreload: bool = False
    web_bind: list[str] = Field(default_factory=lambda: ["localhost:8000"])


class AppConfigurationF(BaseModel):
    app: AppF = Field(default=AppF())


def configure_logging(logconfig_fp: t.Optional[str], debug: t.Optional[bool] = None):
    if logconfig_fp:
        fp = pathlib.Path(logconfig_fp).expanduser()
        if fp.exists():
            logging.config.fileConfig(str(fp))
    # else:
    #     logging.config.dictConfig({"version": 1, "disable_existing_loggers": True})

    # if debug:
    #     for name in logging.root.manager.loggerDict:
    #         logger = logging.getLogger(name)
    #         logger.setLevel(logging.DEBUG)


def configure(
    config_fo: t.Optional[t.TextIO] = None,
    debug: t.Optional[bool] = None,
    logconfig_fp: t.Optional[str] = None,
):
    import toml

    if config_fo:
        config_from_file_data = toml.load(config_fo)
        config_from_file = AppConfigurationF(**config_from_file_data)
    else:
        config_from_file = AppConfigurationF()

    if logconfig_fp is not None:
        config_from_file.app.logconfig_fp = logconfig_fp

    if debug is not None:
        config_from_file.app.debug = debug

    configure_logging(config_from_file.app.logconfig_fp, config_from_file.app.debug)

    return AppConfiguration(**config_from_file.app.model_dump())
