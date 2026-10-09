ARG STACK=system

# -------------------------------- base ------------------------------------------------
# Ubuntu 24.04 comes with libheif 1.17.6, the minimum supported version.
FROM ubuntu:24.04 AS base

SHELL ["/bin/sh", "-ex", "-c"]

ENV LANG=C.UTF-8
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /src

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update \
    && apt-get install --no-install-recommends -y \
        git curl ca-certificates build-essential make \
        python3-dev python3-venv libffi-dev \
        libjpeg-dev libpng-dev libtiff-dev liblcms2-dev

RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m venv /opt/venv \
    && pip install -U pip setuptools


# -------------------------------- libheif-system --------------------------------------
# libheif and binaries from system packages (1.17.6)
FROM base AS libheif-system

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && apt-get install --no-install-recommends -y \
        libheif1 libheif-examples \
        libheif-plugin-libde265 libheif-plugin-x265 libheif-plugin-aomenc


# -------------------------------- libheif-bundled -------------------------------------
FROM libheif-system AS libheif-bundled

ARG LIBHEIF_BINARY=1.23.*

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "libheif-binary==${LIBHEIF_BINARY}"


# -------------------------------- libheif-ucare ---------------------------------------
# Recent libheif and binaries from Uploadcare
FROM base AS libheif-ucare

ARG LIBHEIF_UC=1.23.5-413e2a8-7521f33

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    BUCKET=https://uploadcare-packages.s3.amazonaws.com \
    && curl -fLO $BUCKET/libheif/libheif-uc_${LIBHEIF_UC}_$(dpkg --print-architecture).deb \
    && apt-get update \
    && apt-get install --no-install-recommends -y ./*.deb \
    && rm *.deb


# -------------------------------- development -----------------------------------------
FROM libheif-${STACK} AS development

ARG PILLOW=latest

COPY --parents pyproject.toml setup.py bindings/ pip-stubs/ ./
# Install the binary extension in site-packages. When /src is mounted,
# extend_path lets the local Python package import the installed native extension.
ENV HEIF_IMAGE_PLUGIN_EXTEND_PATH=1
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir _heif_image_plugin \
    && touch README.md HeifImagePlugin.py _heif_image_plugin/__init__.py \
    && pip install --group dev-pillow-${PILLOW} .
