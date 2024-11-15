SOURCE=		custom_components
PYTEST=		pytest

all:

lint:
	ruff check $(SOURCE)

reformat:
	ruff check --select I --fix $(SOURCE)
	ruff format $(SOURCE)

test:
	PYTHONPATH=custom_components $(PYTEST) -vv
