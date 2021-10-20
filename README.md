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

### 0.2.0

* Fill `info['icc_profile']` on loading.
* Close and release file pointer after loading.
* Deconding without custom HeifDecoder(ImageFile.PyDecoder).
