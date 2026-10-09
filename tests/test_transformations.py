from pathlib import Path
from unittest import mock

import pytest
from PIL import Image, ImageOps

from _heif_image_plugin._native import libheif_version
from _heif_image_plugin.reader import open as heif_open
from _heif_image_plugin.transformations import Transformations

from . import avg_diff, respath


def open_with_custom_meta(path, *, exif_data=None, exif=None, crop=None, orientation=0):
    def my_heif_open(*args, **kwargs):
        nonlocal exif_data
        heif = heif_open(*args, **kwargs)
        if exif is not None:
            assert not exif_data  # not at the same time
            exif_data = Image.Exif()
            exif_data.update(exif)
            exif_data = exif_data.tobytes()
        if exif_data is not None:
            heif.metadata = [{'type': 'Exif', 'data': exif_data}]
        else:
            heif.metadata = None
        heif.transformations = Transformations(*heif.size)
        heif.transformations.orientation_tag = orientation
        if crop:
            heif.transformations.crop = crop
        return heif

    with mock.patch('_heif_image_plugin.reader.open') as open_mock:
        open_mock.side_effect = my_heif_open
        image = Image.open(path)
        assert open_mock.called

    return image


def test_no_orientation_and_no_exif():
    image = open_with_custom_meta(respath('test2.heic'), orientation=0)
    assert 'exif' not in image.info


def test_empty_exif():
    image = open_with_custom_meta(respath('test2.heic'), exif_data=b'', orientation=1)
    assert 'exif' in image.info
    assert image.getexif()[274] == 1


def test_broken_exif():
    broken = b'Exif\x00\x00II*\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00'
    image = open_with_custom_meta(respath('test2.heic'),
                                  exif_data=broken, orientation=1)
    assert 'exif' in image.info
    assert image.getexif()[274] == 1


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


@pytest.mark.parametrize('orientation', range(1, 9))
@pytest.mark.parametrize('turn_ccw,flip_horizontal,flip_vertical', [
    (0, False, False), (1, False, False), (2, False, False), (3, False, False),
    (0, True, False), (0, False, True), (1, True, False), (1, False, True),
])
def test_composed_orientation_matches_pixels(orientation, turn_ccw,
                                             flip_horizontal, flip_vertical):
    source = Image.frombytes('L', (5, 3), bytes(range(15)))
    source.getexif()[274] = orientation
    expected = ImageOps.exif_transpose(source)
    for _ in range(turn_ccw):
        expected = expected.transpose(Image.Transpose.ROTATE_90)
    if flip_horizontal:
        expected = expected.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if flip_vertical:
        expected = expected.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    transforms = Transformations(*source.size)
    transforms.orientation_tag = orientation
    transforms.apply_orientation(turn_ccw=turn_ccw, flip_horizontal=flip_horizontal,
                                 flip_vertical=flip_vertical)
    source.getexif()[274] = transforms.orientation_tag
    assert ImageOps.exif_transpose(source) == expected


@pytest.mark.parametrize('orientation', range(1, 9))
def test_crop_before_orientation_matches_pixels(orientation):
    source = Image.frombytes('L', (5, 3), bytes(range(15)))
    source.getexif()[274] = orientation
    expected = ImageOps.exif_transpose(source).crop((1, 1, 3, 2))
    transforms = Transformations(*source.size)
    transforms.orientation_tag = orientation
    transforms.apply_crop(1, 1, 2, 1)
    left, top, width, height = transforms.crop
    cropped = source.crop((left, top, left + width, top + height))
    cropped.getexif()[274] = transforms.orientation_tag
    assert ImageOps.exif_transpose(cropped) == expected


def test_file_transformations_match_libheif():
    data = Path(respath('tree-with-transforms.avif')).read_bytes()
    native = heif_open(data, apply_transformations=False)
    transformed = heif_open(data, apply_transformations=True)
    assert native.transformations == transformed.transformations
    orientation = native.transformations.orientation_tag
    assert 0 <= orientation <= 8
    left, top, width, height = native.transformations.crop
    assert 0 <= left < native.size[0]
    assert 0 <= top < native.size[1]
    assert 1 <= width <= native.size[0] - left
    assert 1 <= height <= native.size[1] - top

    native.load()
    transformed.load()
    pixels = Image.frombytes(
        native.mode, native.size, native.data, 'raw', (native.mode, native.stride))
    pixels = pixels.crop((left, top, left + width, top + height))
    pixels.getexif()[274] = orientation
    expected = Image.frombytes(
        transformed.mode, transformed.size, transformed.data, 'raw',
        (transformed.mode, transformed.stride))
    assert ImageOps.exif_transpose(pixels) == expected


@pytest.mark.xfail(
    (1, 19, 0) <= libheif_version < (1, 22, 0),
    reason='libheif cannot decode this alpha/crop image',
    strict=True,
)
@mock.patch('PIL.ImageFile.LOAD_TRUNCATED_IMAGES', True)
def test_fallback_to_transforms():
    # Image with 695x472 color and 696x472 alpha with crop
    image = Image.open(respath('unreadable-wo-transf.heic'))
    assert image.size == (695, 472)

    ref_image = Image.open(respath('unreadable-wo-transf.ref.heic'))
    avg_diffs = avg_diff(image, ref_image)
    assert max(avg_diffs) <= 0.01
