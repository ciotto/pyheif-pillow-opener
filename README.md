# heif-image-plugin

[![build](https://travis-ci.org/uploadcare/heif-image-plugin.svg?branch=master)](https://travis-ci.org/uploadcare/heif-image-plugin)
[![coverage](https://img.shields.io/codecov/c/gh/uploadcare/heif-image-plugin)](https://codecov.io/gh/uploadcare/heif-image-plugin)
[![Py Versions](https://img.shields.io/pypi/pyversions/heif-image-plugin)](https://pypi.python.org/pypi/heif-image-plugin/)
[![license](https://img.shields.io/github/license/uploadcare/heif-image-plugin)](https://pypi.python.org/pypi/heif-image-plugin/)

Simple HEIF/HEIC images plugin for [Pillow](https://pillow.readthedocs.io)
base on [pyhief](https://github.com/carsales/pyheif#pyheif) library.

Originally based on the [pyheif-pillow-opener](https://github.com/ciotto/pyheif-pillow-opener)
code from Christian Bianciotto.

## Installation

You can install **heif-image-plugin** from *PyPI*:

`pip install heif-image-plugin`

## How to use

Just import once before opening an image.

```python
from PIL import Image
import HeifImagePlugin

image = Image.open('test.heic')
image.load()
```

## How to contribute

This is not a big library but if you want to contribute is very easy!

 1. clone the repository `git clone https://github.com/uploadcare/heif-image-plugin.git`
 1. install all requirements `make init`
 1. do your fixes or add new awesome features (with tests)
 1. run the tests `make test`
 1. commit in new branch and make a pull request


## Changelog

### 0.3.1

! This version requires pyheif with `pyheif.open` API. As of 2021.11.25 this API
isn't released and is in pyheif's master. See `install-pyheif-master-pillow-latest`
target in the `Makefile` to install it.

* Fixed potential vulnerability with arbitrary data in exif metadata.

### 0.3.0

! This version requires pyheif with `pyheif.open` API. As of 2021.11.25 this API
isn't released and is in pyheif's master. See `install-pyheif-master-pillow-latest`
target in the `Makefile` to install it.

* `pyheif.open` API is used for lazy images loading.
* Fixed an error when the plugin tries to load any ISOBMFF files.
* AVIF files should work before, but now this is official.
* Patched versions of `pyheif` and `libheif` with exposed transformations is supported.
  In this case opened image isn't transformed on loading and orientation is stored
  in EXIF `Orientation` tag like for all other image formats.
  This is faster and consumes less memory.

### 0.2.0

* No need to register, works after import.
* Fill `info['icc_profile']` on loading.
* Close and release file pointer after loading.
* Deconding without custom HeifDecoder(ImageFile.PyDecoder).
