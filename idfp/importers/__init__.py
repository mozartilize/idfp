from functools import partial

from idfp.definitions import Type
from idfp.importers.base import import_and_process_csv

importers = {
    Type.AREA: partial(import_and_process_csv, type=Type.AREA),
    Type.STRAIN: partial(import_and_process_csv, type=Type.STRAIN),
}
