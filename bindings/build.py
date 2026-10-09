from pathlib import Path

from cffi import FFI


try:
    import libheif_binary
except ModuleNotFoundError as error:
    if error.name != 'libheif_binary':
        raise
    build_config = {'libraries': ['heif']}
else:
    build_config = libheif_binary.get_build_config()

ffibuilder = FFI()
ffibuilder.cdef(Path(__file__).with_name('libheif_api.h').read_text())
ffibuilder.set_source(
    '_heif_image_plugin._libheif',
    '#include <libheif/heif.h>\n'
    '#include <libheif/heif_properties.h>\n',
    **build_config,
)


if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
