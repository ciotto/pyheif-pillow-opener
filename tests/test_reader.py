import gc
from pathlib import Path

import piexif
import pytest
from PIL import Image

from _heif_image_plugin import reader

from . import respath


@pytest.fixture(params=sorted(
    path for path in Path(respath()).rglob('*')
    if path.suffix.lower() in ('.heic', '.heif', '.hif', '.avif')
    and path.name not in ('test-crop.heic', 'unreadable-wo-transf.heic')
), ids=lambda path: str(path.relative_to(respath())))
def image_path(request):
    return request.param


def test_reader_image_contract(image_path):
    image = reader.open(image_path.read_bytes())
    assert image.size[0] > 0
    assert image.size[1] > 0
    assert isinstance(image.has_alpha, bool)
    assert image.mode == ('RGBA' if image.has_alpha else 'RGB')
    assert image.bit_depth in (8, 10, 12, 16)
    assert image.data is None
    assert image.stride is None

    assert image.load() is image
    assert image.stride >= image.size[0] * len(image.mode)
    assert len(image.data) >= image.stride * image.size[1]
    pixels = Image.frombytes(
        image.mode, image.size, image.data, 'raw', (image.mode, image.stride))
    assert pixels.size == image.size
    assert pixels.mode == image.mode
    data = bytes(image.data)
    stride = image.stride
    assert image.load() is image
    assert image.stride == stride
    assert bytes(image.data) == data


def test_input_bytes_survive_collection_before_loading(image_path):
    data = image_path.read_bytes()
    image = reader.open(data)
    del data
    gc.collect()
    image.load()
    pixels = Image.frombytes(
        image.mode, image.size, image.data, 'raw', (image.mode, image.stride))
    reference = reader.open(image_path.read_bytes()).load()
    expected = Image.frombytes(
        reference.mode, reference.size, reference.data, 'raw',
        (reference.mode, reference.stride))
    assert pixels == expected


def test_real_exif_blocks_are_parseable(image_path):
    image = reader.open(image_path.read_bytes())
    metadata = image.metadata
    image.close()
    for item in metadata or []:
        if item['type'] == 'Exif':
            exif = piexif.load(item['data'])
            assert '0th' in exif
            assert 'Exif' in exif


def test_real_exif_contains_image_and_camera_metadata():
    image = reader.open(Path(respath('test3.heic')).read_bytes())
    metadata = image.metadata
    image.close()
    blocks = [item['data'] for item in metadata or [] if item['type'] == 'Exif']
    assert blocks
    exif = piexif.load(blocks[0])
    assert exif['0th']
    assert exif['Exif']
