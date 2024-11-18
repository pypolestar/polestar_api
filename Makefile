SOURCE=		custom_components
PYTEST=		pytest

all:

lint:
	ruff check $(SOURCE)

reformat:
	ruff check --select I --fix $(SOURCE) tests
	ruff format $(SOURCE) tests

test:
	PYTHONPATH=. $(PYTEST) -vv tests
