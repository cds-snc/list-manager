.PHONY: dev fmt install lint migrations test fmt-ci lint-ci build install-dev load-test

build: ;

dev:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

fmt:
	black . $(ARGS)

install:
	pip3 install --user -r requirements.txt

install-dev:
	pip3 install --user -r requirements_dev.txt

load-test:
	locust

lint:
	flake8 .

lint-ci:
	flake8 .

migrations:
	cd db_migrations &&\
	alembic upgrade head

test:
	API_AUTH_TOKEN=e184bd87-feac-4582-8ec8-dc63557faa68 CI=True coverage run -m pytest -s -vv tests &&\
	coverage report -m

fmt-ci:
	black --check .