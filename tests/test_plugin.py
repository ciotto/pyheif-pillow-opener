from glob import glob
from io import BytesIO
from unittest import mock

import pytest
from PIL import Image, ImageCms, ImageOps
from pyheif.error import HeifError

from HeifImagePlugin import check_heif_magic, pyheif_supports_transformations

from . import avg_diff, respath


@pytest.mark.parametrize(
    'image_name',
    ['test1.heic', 'test2.heic', 'test3.heic', 'test4.heif']
)
def test_load_heic(image_name):
    image = Image.open(respath(image_name))
    image.load()


@pytest.mark.parametrize(
    'image_path',
    list(glob(respath('avif-sample-images', '*.avif')))
)
def test_load_avif(image_path):
    image = Image.open(image_path)
    ref = Image.open(respath('avif-sample-images', 'fox.jpg'))

    if '.monochrome.' in image_path:
        image = image.convert('L')
        ref = ref.convert('L')

    avg_diffs = avg_diff(image, ref, threshold=20)
    assert max(avg_diffs) <= 0.02


def test_open_image_exif():
    image = Image.open(respath('test1.heic'))

    assert image.info['exif'] is not None


def test_open_image_exif_none():
    image = Image.open(respath('test2.heic'))

    assert 'exif' not in image.info


def test_image_color_profile():
    image = Image.open(respath('test3.heic'))

    assert image.info['icc_profile'] is not None

    # Try to parse
    icc_profile = BytesIO(image.info['icc_profile'])
    icc_profile = ImageCms.getOpenProfile(icc_profile)


@mock.patch('pyheif.open', side_effect=HeifError(code=1, subcode=2, message='Error'))
def test_open_image_error(open_mock):
    with pytest.raises(IOError):
        Image.open(respath('test1.heic'))


@mock.patch('pyheif.open')
def test_open_image_metadata(open_mock):
    m = mock.MagicMock()
    m.size = (10, 20)
    m.mode = 'RGB'
    m.data = b'rgb' * 10 * 20
    m.transformations = {'crop': (0, 0, 10, 20), 'orientation_tag': 0}
    m.metadata = [
        {'type': 'foo', 'data': 'bar'},
        {'type': 'bar', 'data': 'foo'},
    ]
    open_mock.return_value = m

    image = Image.open(respath('test1.heic'))

    assert open_mock.called
    assert image is not None


@pytest.mark.parametrize(
    'magic',
    [
        b'heic', b'heix', b'heim', b'heis', b'hevc', b'hevx',
        b'hevm', b'hevs', b'mif1', b'msf1', b'avif', b'avis'
    ]
)
def test_check_heif_magic(magic):
    assert check_heif_magic(b'    ftyp%b    ' % magic)


def test_check_heif_magic_wrong():
    assert not check_heif_magic(b'    ftyphey!    ')


@pytest.mark.parametrize('orientation', list(range(1, 9)))
def test_orientation(orientation, orientation_ref_image):
    image = Image.open(respath('orientation', f'Landscape_{orientation}.heic'))

    if pyheif_supports_transformations:
        # There should be exif in each image, even if Orientation is 0
        assert 'exif' in image.info

        # There should be Orientation tag for each image
        exif = image.getexif()
        assert 0x0112 in exif

        # And this orientation should be the same as in filename
        assert exif[0x0112] == orientation

    # Transposed image shoud be Landscape
    transposed = ImageOps.exif_transpose(image)
    assert transposed.size == (600, 450)

    if pyheif_supports_transformations:
        # Image should change after transposition
        if orientation != 1:
            assert image != transposed

    # The average diff between transposed and original image should be small
    avg_diffs = avg_diff(transposed, orientation_ref_image, threshold=20)
    assert max(avg_diffs) <= 0.02


def test_not_load_truncated():
    image = Image.open(respath('test-crop.heic'))
    with pytest.raises(HeifError):
        image.load()


@mock.patch('PIL.ImageFile.LOAD_TRUNCATED_IMAGES', True)
def test_load_truncated():
    image = Image.open(respath('test-crop.heic'))
    image.load()
