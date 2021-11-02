import pytest
from PIL import Image


@pytest.fixture(scope="session")
def orientation_ref_image():
    return Image.open(res('orientation', 'Landscape_1.heic'))
