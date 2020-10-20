import os
from unittest import mock

import PIL
import pytest
from PIL import Image
from pyheif.error import HeifError

from pyheif_pillow_opener import register_heif_opener, check_heif_magic

register_heif_opener()


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


@mock.patch('pyheif_pillow_opener.check_heif_magic', return_value=False)
def test_open_image_short(check_heif_magic_mock):
    with pytest.raises(PIL.UnidentifiedImageError):
        Image.open(os.path.join('tests', 'images', 'test1.heic'))


@mock.patch('pyheif.read', side_effect=HeifError(code=1, subcode=2, message='Error'))
def test_open_image_error(read_mock):
    with pytest.raises(PIL.UnidentifiedImageError):
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


@mock.patch.object(Image, 'register_open')
@mock.patch.object(Image, 'register_decoder')
@mock.patch.object(Image, 'register_extensions')
@mock.patch.object(Image, 'register_mime')
def test_register_heif_opener(
    register_open_mock,
    register_decoder_mock,
    register_extensions_mock,
    register_mime_mock,
):
    register_heif_opener()

    register_open_mock.assert_called_once()
    register_decoder_mock.assert_called_once()
    register_extensions_mock.assert_called_once()
    register_mime_mock.assert_called_once()
