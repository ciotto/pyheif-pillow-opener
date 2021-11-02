from io import BytesIO
from unittest import mock

import pytest
from PIL import Image, ImageCms, ImageOps
from pyheif import read as pyheif_read
from pyheif.error import HeifError

from HeifImagePlugin import check_heif_magic

from . import avg_diff, respath


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
    image = Image.open(respath(image_name))
    image.load()


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


@mock.patch('pyheif.read', side_effect=HeifError(code=1, subcode=2, message='Error'))
def test_open_image_error(read_mock):
    with pytest.raises(IOError):
        Image.open(respath('test1.heic'))


@mock.patch('pyheif.read')
def test_open_image_metadata(read_mock):
    m = mock.MagicMock()
    m.size = (10, 20)
    m.mode = 'RGB'
    m.data = b'rgb' * 10 * 20
    m.transformations = {'crop': (0, 0, 10, 20), 'orientation_tag': 0}
    m.metadata = [
        {'type': 'foo', 'data': 'bar'},
        {'type': 'bar', 'data': 'foo'},
    ]
    read_mock.return_value = m

    image = Image.open(respath('test1.heic'))

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


@pytest.mark.parametrize('orientation', list(range(1, 9)))
def test_orientation(orientation, orientation_ref_image):
    image = Image.open(respath('orientation', f'Landscape_{orientation}.heic'))

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

    # Image should change after transposition
    if orientation != 1:
        assert image != transposed

    # The average diff between transposed and original image should be small
    avg_diffs = avg_diff(transposed, orientation_ref_image, threshold=20)
    assert max(avg_diffs) <= 0.02


def open_with_custom_meta(path, *, exif=None, crop=None, orientation=0):
    def my_pyheif_read(*args, **kwargs):
        heif = pyheif_read(*args, **kwargs)
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

    with mock.patch('pyheif.read') as read_mock:
        read_mock.side_effect = my_pyheif_read
        image = Image.open(path)
        assert read_mock.called

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
