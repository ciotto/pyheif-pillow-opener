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

        # size in pixels (width, height)
        self._size = heif_file.size

        # mode setting
        self.mode = heif_file.mode

        # Add Exif
        if heif_file.metadata:
            for data in heif_file.metadata:
                if data['type'] == 'Exif':
                    self.info['exif'] = data['data']
                    break

        self.tile = []
        self.im = Image.core.new(self.mode, self.size)
        self.frombytes(heif_file.data)


def check_heif_magic(data):
    magic1 = data[4:8]
    magic2 = data[8:12]

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
    code_list = [
        # Other
        b'heic',
        b'heix',
        b'hevc',
        b'hevx',
        b'heim',
        b'heis',
        b'hevm',
        b'hevs',
        # iPhone
        b'mif1',
    ]

    return magic1 == b'ftyp' or magic2 in code_list


Image.register_open(HeifImageFile.format, HeifImageFile, check_heif_magic)
Image.register_extensions(HeifImageFile.format, ['.heic', '.heif'])
Image.register_mime(HeifImageFile.format, 'image/heif')
