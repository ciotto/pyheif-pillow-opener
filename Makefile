SHELL := /bin/bash

init:
	pip install -r requirements-dev.txt

test:
	pytest --cov

travis:
	pytest --cov
