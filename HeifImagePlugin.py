import inspect
from copy import copy
from weakref import WeakKeyDictionary

import piexif
import pyheif
from cffi import FFI
from PIL import Image, ImageFile
from pyheif.error import HeifError


ffi = FFI()
_keep_refs = WeakKeyDictionary()
pyheif_supports_transformations = (
    'transformations' in inspect.signature(pyheif.HeifFile).parameters
)


def _crop_heif_file(heif):
    # Zero-copy crop before loading. Just shifts data pointer and updates meta.
    crop = heif.transformations['crop']
    if crop == (0, 0) + heif.size:
        return heif

    if heif.mode not in ("L", "RGB", "RGBA"):
        raise ValueError("Unknown mode")
    pixel_size = len(heif.mode)

    offset = heif.stride * crop[1] + pixel_size * crop[0]
    cdata = ffi.from_buffer(heif.data, require_writable=False) + offset
    data = ffi.buffer(cdata, heif.stride * crop[3])

    # Keep reference to the original data as long as "cdata + offset" is alive.
    # Normally ffi.from_buffer should hold it for us but unfortunately
    # cdata + offset creates a new cdata object without reference.
    _keep_refs[cdata] = heif.data

    new_heif = copy(heif)
    new_heif.size = crop[2:4]
    new_heif.transformations = dict(heif.transformations, crop=(0, 0) + crop[2:4])
    new_heif.data = data
    return new_heif


def _rotate_heif_file(heif):
    """
    Heif files already contain transformation chunks imir and irot which are
    dominate over Orientation tag in EXIF.

    This is not aligned with other formats behaviour and we MUST fix EXIF after
    loading to prevent unexpected rotation after resaving in other formats.

    And we come up to there is no reasons to force rotation of HEIF images
    after loading since we need update EXIF anyway.
    """
    orientation = heif.transformations['orientation_tag']
    if not (1 <= orientation <= 8):
        return heif

    exif_id = None
    for i, data in enumerate(heif.metadata or []):
        if data['type'] == 'Exif':
            exif_id = i
            break

    new_heif = copy(heif)
    new_heif.metadata = (heif.metadata or []).copy()
    new_heif.transformations = dict(heif.transformations, orientation_tag=0)

    if exif_id is None:
        exif = {'0th': {piexif.ImageIFD.Orientation: orientation}}
        new_heif.metadata.append({'type': 'Exif', 'data': piexif.dump(exif)})
    else:
        exif = piexif.load(heif.metadata[exif_id]['data'])
        exif['0th'][piexif.ImageIFD.Orientation] = orientation
        new_heif.metadata[exif_id] = {'type': 'Exif', 'data': piexif.dump(exif)}
    return new_heif


class HeifImageFile(ImageFile.ImageFile):
    format = 'HEIF'
    format_description = "HEIF/HEIC image"

    def _open(self):
        try:
            heif_file = pyheif.open(
                self.fp, apply_transformations=not pyheif_supports_transformations)
        except HeifError as e:
            raise SyntaxError(str(e))

        if self._exclusive_fp:
            self.fp.close()
        self.fp = None

        if pyheif_supports_transformations:
            heif_file = _rotate_heif_file(heif_file)
            self._size = heif_file.transformations['crop'][2:4]
        else:
            self._size = heif_file.size

        self.mode = heif_file.mode

        if heif_file.metadata:
            for data in heif_file.metadata:
                if data['type'] == 'Exif':
                    self.info['exif'] = data['data']
                    break

        if heif_file.color_profile:
            # rICC is Restricted ICC. Still not sure can it be used.
            # ISO/IEC 23008-12 says: The colour information 'colr' descriptive
            # item property has the same syntax as the ColourInformationBox
            # as defined in ISO/IEC 14496-12.
            # ISO/IEC 14496-12 says: Restricted profile shall be of either
            # the Monochrome or Three‐Component Matrix‐Based class of
            # input profiles, as defined by ISO 15076‐1.
            # We need to go deeper...
            if heif_file.color_profile['type'] in ('rICC', 'prof'):
                self.info['icc_profile'] = heif_file.color_profile['data']

        self.tile = []
        self.heif_file = heif_file

    def load(self):
        if self.heif_file:
            heif_file = self.heif_file.load()
            if pyheif_supports_transformations:
                heif_file = _crop_heif_file(heif_file)

            self.load_prepare()
            self.frombytes(heif_file.data, "raw", (self.mode, heif_file.stride))
            self.heif_file.data = None
            self.heif_file = None

        return super().load()


def check_heif_magic(data):
    return pyheif.check(data) != pyheif.heif_filetype_no


Image.register_open(HeifImageFile.format, HeifImageFile, check_heif_magic)
Image.register_mime(HeifImageFile.format, 'image/heif')
