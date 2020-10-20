# pyheif-pillow-opener

[![build](https://travis-ci.org/ciotto/pyheif-pillow-opener.svg?branch=master)](https://travis-ci.org/ciotto/pyheif-pillow-opener)
[![coverage](https://img.shields.io/codecov/c/gh/ciotto/pyheif-pillow-opener)](https://codecov.io/gh/ciotto/pyheif-pillow-opener)
[![Py Versions](https://img.shields.io/pypi/pyversions/pyheif-pillow-opener)](https://pypi.python.org/pypi/pyheif-pillow-opener/)
[![license](https://img.shields.io/github/license/ciotto/pyheif-pillow-opener)](https://pypi.python.org/pypi/pyheif-pillow-opener/)
[![status](https://img.shields.io/pypi/status/pyheif-pillow-opener)](https://pypi.python.org/pypi/pyheif-pillow-opener/)
[![PEP8](https://img.shields.io/badge/code%20style-pep8-orange)](https://www.python.org/dev/peps/pep-0008/)

**pyheif-pillow-opener** is a *simple* HEIF/HEIC opener for *Pillow* base on *pyhief* library.

## Installation

You can install **pyheif-pillow-opener** from *PyPi*:

`pip install pyheif-pillow-opener`

or from GitHub:

`pip install https://github.com/ciotto/pyheif-pillow-opener/archive/master.zip`

## How to use

```
from PIL import Image

from pyheif_pillow_opener import register_heif_opener

register_heif_opener()

image = Image.open('test.heic')
image.load()
```

## How to contribute

This is not a big library but if you want to contribute is very easy!

 1. clone the repository `git clone https://github.com/ciotto/pyheif-pillow-opener.git`
 1. install all requirements `make init`
 1. do your fixes or add new awesome features (with tests)
 1. run the tests `make test`
 1. commit in new branch and make a pull request

---


## License

Released under [MIT License](https://github.com/ciotto/pyheif-pillow-opener/blob/master/LICENSE).
