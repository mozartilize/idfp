import multiprocessing
from gunicorn.glogging import Logger as _Logger


class DisabledLogger(_Logger):
    def setup(self, cfg):
        pass


wsgi_app = "idfp.web:app_factory()"
# disable gunicorn loggers, use our own
logger_class = DisabledLogger
# set this to anything to force gunicorn log on requests
accesslog = "-"
workers = multiprocessing.cpu_count() * 2 + 1
