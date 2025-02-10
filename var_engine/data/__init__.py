from pathlib import Path

from pkg_resources import resource_filename

DATA_SOURCE = Path(resource_filename(__name__, "/"))

EXAMPLE_PATH = DATA_SOURCE / "template/example.xlsx"
