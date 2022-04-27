import os
import tempfile
from io import BytesIO

from PIL import Image

from . import avg_diff


def test_save_to_filename(fox_small_image):
    f, filename = tempfile.mkstemp('.avif')
    os.close(f)
    try:
        fox_small_image.save(filename)
        image = Image.open(filename)
        assert image.format == 'HEIF'
        avg_diffs = avg_diff(image, fox_small_image, threshold=10)
        assert max(avg_diffs) <= 0.02
    finally:
        os.unlink(filename)


def test_save_to_fp(fox_small_image):
    f, filename = tempfile.mkstemp('.avif')
    os.close(f)
    try:
        with open(filename, 'wb') as fp:
            fox_small_image.save(fp)
        image = Image.open(filename)
        assert image.format == 'HEIF'
        avg_diffs = avg_diff(image, fox_small_image, threshold=10)
        assert max(avg_diffs) <= 0.02
    finally:
        os.unlink(filename)


def test_save_to_bytesio(fox_small_image):
    with BytesIO() as fp:
        fox_small_image.save(fp, format='HEIF', avif=True)
        fp.seek(0)
        image = Image.open(fp)
        assert image.format == 'HEIF'
        avg_diffs = avg_diff(image, fox_small_image, threshold=10)
        assert max(avg_diffs) <= 0.02
