import logging
from flask import Flask

from idfp.config import AppConfiguration

logger = logging.getLogger(__name__)


def create_app(config: AppConfiguration):
    app = Flask('idfp')
    app.config.update(
        SECRET_KEY=config.secret_key,
        DEBUG=config.debug,  # might not useful unless use flask cli
    )
    app.config['config'] = config

    from idfp.web.views import (
        index_view,
        sources_views,
        csv_errors_download,
        query_view,
    )
    app.route("/")(index_view)
    app.route("/sources")(sources_views)
    app.route("/csv-errors/download")(csv_errors_download)
    app.route("/query", methods=["GET", "POST"])(query_view)

    if config.debug:
        from werkzeug.debug import DebuggedApplication

        # looks cool but somehow not totally work
        # like, print the variable in the same context (frame)
        # will check later
        app = DebuggedApplication(app, evalex=True)
        logger.debug(f"Debugger PIN: {app.pin}")

    return app


app = None
