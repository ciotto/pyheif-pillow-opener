import os
from unittest import mock

import pytest
from PIL import Image
from pyheif.error import HeifError

from HeifImagePlugin import check_heif_magic


@pytest.mark.parametrize(
    ['image_name'],
    [
        ('test1.heic',),
        ('test2.heic',),
        ('test3.heic',),
        ('test4.heif',),
    ]
)
def test_open_image(image_name):
    image = Image.open(os.path.join('tests', 'images', 'test1.heic'))
    image.load()

    assert image is not None


def test_open_image_exif():
    image = Image.open(os.path.join('tests', 'images', 'test1.heic'))

    assert image.info['exif'] is not None


def test_open_image_exif_none():
    image = Image.open(os.path.join('tests', 'images', 'test2.heic'))

    assert 'exif' not in image.info


@mock.patch('HeifImagePlugin.check_heif_magic', return_value=False)
def test_open_image_short(check_heif_magic_mock):
    with pytest.raises(IOError):
        Image.open(os.path.join('tests', 'images', 'test1.heic'))


@mock.patch('pyheif.read', side_effect=HeifError(code=1, subcode=2, message='Error'))
def test_open_image_error(read_mock):
    with pytest.raises(IOError):
        Image.open(os.path.join('tests', 'images', 'test1.heic'))


@mock.patch('pyheif.read')
def test_open_image_metadata(read_mock):
    m = mock.MagicMock()
    m.size = (10, 20)
    m.mode = 'RGB'
    m.metadata = [
        {'type': 'foo', 'data': 'bar'},
        {'type': 'bar', 'data': 'foo'},
    ]
    read_mock.return_value = m

    image = Image.open(os.path.join('tests', 'images', 'test1.heic'))

    assert image is not None


@pytest.mark.parametrize(
    ['magic'],
    [
        (b'heic',),
        (b'heix',),
        (b'hevc',),
        (b'hevx',),
        (b'heim',),
        (b'heis',),
        (b'hevm',),
        (b'hevs',),
        (b'mif1',),
    ]
)
def test_check_heif_magic(magic):
    assert check_heif_magic(b'    ftyp%b    ' % magic)


def test_check_heif_magic_wrong():
    assert not check_heif_magic(b'    fty hei     ')
