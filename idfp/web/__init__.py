from flask import Flask, current_app

from idfp.config import AppConfiguration


def create_app(config: AppConfiguration):
    app = Flask('idfp')
    app.config.update(
        SECRET_KEY=config.secret_key,
    )
    app.config['config'] = config

    from idfp.web.views import (
        index_view,
        sources_views,
        csv_errors_download,
    )
    app.route("/")(index_view)
    app.route("/sources")(sources_views)
    app.route("/csv-errors/download")(csv_errors_download)

    @app.route("/hello")
    def hello():
        return f"Hello {current_app.config['config'].name}!"

    return app


app = None
