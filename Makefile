.PHONY: clean lint commit check

xargs=$(if $(shell xargs -r </dev/null 2>/dev/null && echo 1), xargs -r, xargs)

clean:
	find . -type f \( -name \*.pyc -o -name \*.pyo \) -delete
	find . -type d -name __pycache__ -print0 | $(xargs) -0 rm -rf

lint: clean
	isort --diff HeifImagePlugin.py ./tests
	pycodestyle HeifImagePlugin.py ./tests
	flake8 HeifImagePlugin.py ./tests

GIT_DIFF=git diff --name-only --cached --diff-filter=dt
commit:
	${GIT_DIFF} -- '*.py' | $(xargs) isort --diff
	${GIT_DIFF} -- '*.py' | $(xargs) pycodestyle
	${GIT_DIFF} -- '*.py' | $(xargs) flake8

check: clean
	pytest --cov=. --cov-report=xml tests


.PHONY: install-pillow-latest install-pillow-prod

install-pillow-latest:
	pip install --use-deprecated=legacy-resolver .[test] \
		-e git+https://github.com/uploadcare/pyheif.git@prod-avif-tests#egg=pyheif

install-pillow-prod:
	sudo apt install --no-install-recommends -y libjpeg-dev
	pip install --use-deprecated=legacy-resolver .[test] \
		-e git+https://github.com/uploadcare/pillow-simd.git@simd/6.0-cmyk16bit#egg=pillow \
		-e git+https://github.com/uploadcare/pyheif.git@prod-avif-tests#egg=pyheif
