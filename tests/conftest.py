import pytest
from PIL import Image

from . import respath


@pytest.fixture(scope="session")
def orientation_ref_image():
    return Image.open(respath('orientation', 'Landscape_1.heic'))
