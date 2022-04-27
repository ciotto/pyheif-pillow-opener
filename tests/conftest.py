import pytest
from PIL import Image

from . import respath


@pytest.fixture(scope="session")
def orientation_ref_image():
    return Image.open(respath('orientation', 'Landscape_1.heic'))


@pytest.fixture(scope="session")
def fox_ref_image():
    return Image.open(respath('avif-sample-images', 'fox.jpg'))


@pytest.fixture(scope="session")
def fox_small_image(fox_ref_image):
    return fox_ref_image.resize((256, 170), Image.BICUBIC)
