from copy import copy

import cffi
import pyheif
from PIL import Image, ImageFile
from pyheif.error import HeifError


ffi = FFI()


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
    
    new_heif = copy(heif)
    new_heif.size = crop[2:4]
    new_heif.transformations = dict(heif.transformations, crop=(0, 0) + crop[2:4])
    new_heif.data = data
    return new_heif


def _rotate_heif_file(heif):
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
        exif = Image.Exif()
        exif[0x0112] = orientation
        new_heif.metadata.append({'type': 'Exif', 'data': exif.tobytes()})
    else:
        exif_data = heif.metadata[exif_id]['data']
        # TODO: patch or amend exif
        new_heif.metadata[exif_id] ={'type': 'Exif', 'data': exif_data}
    return new_heif


class HeifImageFile(ImageFile.ImageFile):
    format = 'HEIF'
    format_description = "HEIF/HEIC image"

    def _open(self):
        try:
            heif_file = pyheif.read(self.fp, apply_transformations=False)
        except HeifError as e:
            raise SyntaxError(str(e))

        if self._exclusive_fp:
            self.fp.close()
        self.fp = None

        heif_file = _crop_heif_file(heif_file)
        heif_file = _rotate_heif_file(heif_file)

        self.mode = heif_file.mode
        self._size = heif_file.size

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
        self.load_prepare()
        self.frombytes(heif_file.data, "raw", (self.mode, heif_file.stride))


# https://github.com/strukturag/libheif/issues/83
# https://github.com/GNOME/gimp/commit/e4bff4c8016f18195f9a6229f59cbf41740ddb8d
# 'heic': the usual HEIF images
# 'heix': 10bit images, or anything that uses h265 with range extension
# 'hevc', 'hevx': brands for image sequences
# 'heim': multiview
# 'heis': scalable
# 'hevm': multiview sequence
# 'hevs': scalable sequence
# 'hevs': scalable sequence
heif_codes = {
    b'heic',
    b'heix',
    b'hevc',
    b'hevx',
    b'heim',
    b'heis',
    b'hevm',
    b'hevs',
    b'mif1',  # iPhone
}

def check_heif_magic(data):
    return data[4:8] == b'ftyp' or data[8:12] in heif_codes


Image.register_open(HeifImageFile.format, HeifImageFile, check_heif_magic)
Image.register_extensions(HeifImageFile.format, ['.heic', '.heif'])
Image.register_mime(HeifImageFile.format, 'image/heif')
