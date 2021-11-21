from unittest import mock

from PIL import Image
from pyheif import open as pyheif_open

from . import respath


def open_with_custom_meta(path, *, exif=None, crop=None, orientation=0):
    def my_pyheif_open(*args, **kwargs):
        heif = pyheif_open(*args, **kwargs)
        if exif is None:
            heif.metadata = None
        else:
            exif_data = Image.Exif()
            exif_data.update(exif)
            heif.metadata = [{'type': 'Exif', 'data': exif_data.tobytes()}]
        heif.transformations = {
            'crop': crop if crop else (0, 0) + heif.size,
            'orientation_tag': orientation,
        }
        return heif

    with mock.patch('pyheif.open') as open_mock:
        open_mock.side_effect = my_pyheif_open
        image = Image.open(path)
        assert open_mock.called

    return image


def test_no_orientation_and_no_exif():
    image = open_with_custom_meta(respath('test2.heic'), orientation=0)
    assert 'exif' not in image.info


def test_orientation_and_no_exif():
    image = open_with_custom_meta(respath('test2.heic'), orientation=7)

    assert 'exif' in image.info
    assert image.getexif()[274] == 7


def test_no_orientation_and_exif_with_rotation():
    image = open_with_custom_meta(
        respath('test2.heic'), orientation=0, exif={274: 7})

    assert 'exif' in image.info
    assert image.getexif()[274] == 7


def test_orientation_and_exif_with_rotation():
    # Orientation tag from file should suppress Exif value
    image = open_with_custom_meta(
        respath('test2.heic'), orientation=1, exif={274: 7})

    assert 'exif' in image.info
    assert image.getexif()[274] == 1


def test_orientation_and_exif_without_rotation():
    image = open_with_custom_meta(
        respath('test2.heic'), orientation=1, exif={270: "Sample image"})

    assert 'exif' in image.info
    assert image.getexif()[274] == 1


def test_crop_on_load():
    ref_image = Image.open(respath('test2.heic'))
    assert ref_image.size == (1280, 720)

    image = open_with_custom_meta(respath('test2.heic'), crop=(0, 0, 512, 256))
    assert image.size == (512, 256)
    assert image.copy() == ref_image.crop((0, 0, 512, 256))

    image = open_with_custom_meta(respath('test2.heic'), crop=(99, 33, 512, 256))
    assert image.size == (512, 256)
    assert image.copy() == ref_image.crop((99, 33, 611, 289))
