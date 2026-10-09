XARGS := $(if $(shell echo | xargs -r 2>/dev/null && echo 1), xargs -r, xargs)
GIT_DIFF := git diff --name-only --cached --diff-filter=dt


.PHONY: commit
commit:
	$(GIT_DIFF) -- '*.py' | $(XARGS) isort --check-only --diff
	$(GIT_DIFF) -- '*.py' | $(XARGS) flake8


.PHONY: lint
lint:
	isort --check-only --diff HeifImagePlugin.py _heif_image_plugin bindings setup.py ./tests
	flake8 HeifImagePlugin.py _heif_image_plugin bindings setup.py ./tests


.PHONY: test
test:
	pytest --cov=HeifImagePlugin --cov=_heif_image_plugin


ARCH ?= amd64
STACK ?= system
PILLOW ?=
LIBHEIF_UC ?=
LIBHEIF_BINARY ?=


.PHONY: dockerignore
dockerignore:
	@git status -s --ignored | sed -n 's/^!! /\//p' > .dockerignore
	@printf "%s\n" "/.git*" >> .dockerignore


.PHONY: docker_build
docker_build: dockerignore
	docker build --platform=linux/${ARCH} \
		--build-arg STACK=${STACK} \
		$(if $(PILLOW),--build-arg PILLOW=$(PILLOW)) \
		$(if $(LIBHEIF_UC),--build-arg LIBHEIF_UC=$(LIBHEIF_UC)) \
		$(if $(LIBHEIF_BINARY),--build-arg LIBHEIF_BINARY=$(LIBHEIF_BINARY)) \
		-t heif-image-plugin:latest .


.PHONY: docker_shell
docker_shell: docker_build
	docker run --platform=linux/${ARCH} --rm -it -v .:/src heif-image-plugin:latest
