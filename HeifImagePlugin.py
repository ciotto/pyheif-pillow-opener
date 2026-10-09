import subprocess
import tempfile

from PIL import Image, ImageFile

from _heif_image_plugin import reader
from _heif_image_plugin._native import HEIF_ENC_BIN, libheif_version
from _heif_image_plugin.errors import Errors, HeifError, LibheifError  # noqa: F401
from _heif_image_plugin.metadata import (
    extract_heif_exif as _extract_heif_exif, rotate_heif_file as _rotate_heif_file)
from _heif_image_plugin.transformations import crop_heif_file as _crop_heif_file


class HeifImageFile(ImageFile.ImageFile):
    format = 'HEIF'
    format_description = "HEIF/HEIC image"

    def _open_heif_file(self, apply_transformations):
        try:
            heif_file = reader.open(
                self.fp.read(), apply_transformations=apply_transformations)
        except HeifError as e:
            raise SyntaxError(str(e))

        _extract_heif_exif(heif_file)

        if apply_transformations:
            self._size = heif_file.size
        else:
            heif_file = _rotate_heif_file(heif_file)
            self._size = heif_file.transformations.crop[2:4]

        if hasattr(self, "_mode"):
            self._mode = heif_file.mode
        else:
            # Fallback for Pillow < 10.1.0
            # https://pillow.readthedocs.io/en/stable/releasenotes/10.1.0.html#setting-image-mode
            self.mode = heif_file.mode

        self.info.pop('exif', None)
        self.info.pop('icc_profile', None)

        if heif_file.exif:
            self.info['exif'] = heif_file.exif

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
        return heif_file

    def _open(self):
        self.tile = []
        self.heif_file = self._open_heif_file(False)

    def load(self):
        heif_file, self.heif_file = self.heif_file, None
        if heif_file:
            try:
                try:
                    heif_file = heif_file.load(
                        strict_decoding=not ImageFile.LOAD_TRUNCATED_IMAGES)
                except HeifError as e:
                    if e != Errors.unsupported_color_conversion:
                        raise
                    # Unsupported feature: Unsupported color conversion
                    # https://github.com/strukturag/libheif/issues/1273
                    self.fp.seek(0)
                    heif_file = self._open_heif_file(True).load(
                        strict_decoding=not ImageFile.LOAD_TRUNCATED_IMAGES)
            except HeifError as e:
                # Ignore EOF error and return blank image otherwise
                cropped_file = e == Errors.end_of_file
                if not cropped_file or not ImageFile.LOAD_TRUNCATED_IMAGES:
                    raise

            self.load_prepare()

            if heif_file.data:
                heif_file = _crop_heif_file(heif_file)
                self.frombytes(heif_file.data, "raw", (self.mode, heif_file.stride))

            heif_file.data = None

        return super().load()


def check_heif_magic(data):
    return reader.check(data)


is_buggy_la_mode = (1, 17, 0) <= libheif_version <= (1, 18, 2)


def _save(im, fp, filename):
    # Save it before subsequent im.save() call
    info = im.encoderinfo

    if im.mode in ('P', 'PA'):
        # disbled due to errors in libheif encoder
        raise IOError("cannot write mode P as HEIF")

    if im.mode == '1':
        # to circumvent `heif-enc` bug
        im = im.convert('L')

    if im.mode == 'LA' and is_buggy_la_mode:
        im = im.convert('RGBA')

    with tempfile.NamedTemporaryFile(suffix='.png') as tmpfile:
        im.save(
            tmpfile, format='PNG', optimize=False, compress_level=0,
            icc_profile=info.get('icc_profile', im.info.get('icc_profile')),
            exif=info.get('exif', im.info.get('exif'))
        )

        cmd = [HEIF_ENC_BIN, '-o', '/dev/stdout', tmpfile.name]

        avif = info.get('avif')
        if avif is None and filename:
            ext = filename.rpartition('.')[2].lower()
            avif = ext == 'avif'
        if avif:
            cmd.append('-A')

        if info.get('encoder'):
            cmd.extend(['-e', str(info['encoder'])])

        if info.get('quality') is not None:
            cmd.extend(['-q', str(info['quality'])])

        cmd.extend(['-C', str(info.get('downsampling') or 'average')])

        is_svt = info.get('encoder') == 'svt'
        subsampling = info.get('subsampling')
        if subsampling is None:
            subsampling = '420'
        if subsampling == 0:
            subsampling = '444'
        elif subsampling == 1:
            subsampling = '422'
        elif subsampling == 2:
            subsampling = '420'
        if is_svt:
            if subsampling != '420':
                raise ValueError('SVT encoder supports only subsampling=420')
        else:
            cmd.extend(['-p', f'chroma={subsampling}'])

        if avif and info.get('concurrency') is not None:
            cmd.extend(['-p', f"threads={info['concurrency']}"])

        params = dict(info.get('encoder_params') or {})
        if is_svt and 'chroma' in params:
            raise ValueError('SVT encoder does not support chroma parameter')
        if (speed := info.get('speed')) is not None:
            params.setdefault('speed', speed)
        for k, v in params.items():
            cmd.extend(['-p', f'{k}={v}'])

        try:
            with tempfile.TemporaryFile() as stderr:
                with subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=stderr
                ) as enc:
                    for data in iter(lambda: enc.stdout.read(128 * 1024), b''):
                        fp.write(data)
                    if enc.wait():
                        stderr.seek(0)
                        message = stderr.read().decode(errors='replace').strip()
                        if not message:
                            message = f'heif-enc exited with code {enc.returncode}'
                        raise OSError(message)
        except FileNotFoundError:
            raise FileNotFoundError(
                2, f"Can't find heif encoding binary. Install '{HEIF_ENC_BIN}' "
                + "or set `HeifImagePlugin.HEIF_ENC_BIN` to full path.")


Image.register_open(HeifImageFile.format, HeifImageFile, check_heif_magic)
Image.register_save(HeifImageFile.format, _save)
Image.register_mime(HeifImageFile.format, 'image/heif')
Image.register_extensions(HeifImageFile.format, [".heic", ".avif"])

# Don't use this extensions for saving images, use the ones above.
# They have added for quick file type detection only (i.g. by Django).
Image.register_extensions(HeifImageFile.format, [".heif", ".hif"])
