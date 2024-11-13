from glob import glob

from gunicorn.glogging import Logger as _Logger


class DisabledLogger(_Logger):
    def setup(self, cfg):
        pass


wsgi_app = "idfp.web:app_factory()"
# logger_class = DisabledLogger
