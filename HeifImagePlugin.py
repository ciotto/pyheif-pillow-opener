import pyheif
from PIL import Image, ImageFile
from pyheif.error import HeifError


class HeifImageFile(ImageFile.ImageFile):
    format = 'HEIF'
    format_description = "HEIF/HEIC image"

    def _open(self):
        try:
            heif_file = pyheif.read(self.fp)
        except HeifError as e:
            raise SyntaxError(str(e))

        if self._exclusive_fp:
            self.fp.close()
        self.fp = None

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
