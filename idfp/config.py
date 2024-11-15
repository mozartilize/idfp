import collections.abc
import logging.config
import typing as t
import secrets
from dataclasses import dataclass

from pydantic import BaseModel, Field


def update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


@dataclass
class AppConfiguration:
    secret_key: str
    debug: bool
    dbname: str = "idfp"
    dbhost: t.Optional[str] = None
    dbport: t.Optional[int] = None
    dbuser: str = "postgres"
    dbpassword: t.Optional[str] = None
    dbreaderuser: str = "postgres"
    dbreaderpassword: t.Optional[str] = None
    web_bind: list[str] = Field(default_factory=lambda: ["localhost:8000"])
    web_workers: t.Optional[int] = None
    web_preload: bool = False
    web_reuse_port: bool = False


class AppF(BaseModel):
    secret_key: str = Field(default_factory=secrets.token_hex)
    dbname: str = 'idfp'
    dbhost: t.Optional[str] = None
    dbport: t.Optional[int] = None
    dbuser: str = 'postgres'
    dbpassword: t.Optional[str] = None
    dbreaderuser: str = "postgres"
    dbreaderpassword: t.Optional[str] = None
    debug: bool = False
    web_bind: list[str] = Field(default_factory=lambda: ["localhost:8000"])
    web_workers: t.Optional[int] = None
    web_preload: bool = False
    web_reuse_port: bool = False


class AppConfigurationF(BaseModel):
    app: AppF = Field(default=AppF())
    logging: dict[str, t.Any] = Field(default_factory=dict)


def configure_logging(logging_cfg, debug: t.Optional[bool] = None):
    default = {
        "version": 1,
        "disable_existing_loggers": True,
        "handlers": {
            "null_handler": {
                "level": "DEBUG",
                "class": "logging.NullHandler",
            },
        },
        'loggers': {
            '': {  # this is root logger
                'level': 'INFO',
                'handlers': ['null_handler'],
            },
        }
    }
    update(default, logging_cfg)
    logging.config.dictConfig(default)


def configure(
    config_fo: t.Optional[t.BinaryIO] = None,
    debug: t.Optional[bool] = None,
    logconfig_fp: t.Optional[str] = None,
):
    import tomllib

    if config_fo:
        config_from_file_data = tomllib.load(config_fo)
        config_from_file = AppConfigurationF(**config_from_file_data)
    else:
        config_from_file = AppConfigurationF()

    if debug is not None:
        config_from_file.app.debug = debug

    configure_logging(config_from_file.logging, config_from_file.app.debug)

    return AppConfiguration(**config_from_file.app.model_dump())
