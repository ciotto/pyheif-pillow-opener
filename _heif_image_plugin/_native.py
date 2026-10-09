import ctypes
import os
import sys
import warnings
from pathlib import Path


# Transformation APIs exist in 1.16, but 1.17 adds heif_properties.h and
# 4:2:2 <-> 4:4:4 color conversion needed for AVIF subsampling='422'.
MIN_VERSION = (1, 17, 0)

INSTALL_HINT = (
    "Try installing 'heif-image-plugin[libheif]' or 'libheif-binary>=1.17.6.2'."
)


def _load_bundled_library():
    try:
        import libheif_binary
    except ModuleNotFoundError as error:
        if error.name != 'libheif_binary':
            raise
    else:
        try:
            encoder = libheif_binary.get_executable('heif-enc')
            handle = libheif_binary.load_library()
        except (OSError, ValueError, AttributeError) as error:
            warnings.warn(
                f'Cannot use libheif_binary: {error}; trying system libheif.',
                RuntimeWarning, stacklevel=2,
            )
        else:
            return handle, encoder

    return None, 'heif-enc'


_library_handle, HEIF_ENC_BIN = _load_bundled_library()

try:
    from ._libheif import ffi, lib  # noqa: F401
except ImportError as error:
    if _library_handle is None and sys.platform == 'darwin':
        prefix = os.environ.get('HOMEBREW_PREFIX', '/opt/homebrew')
        candidate = Path(prefix) / 'lib' / 'libheif.dylib'
        if candidate.is_file():
            dylib = str(candidate)
            try:
                _library_handle = ctypes.CDLL(dylib, mode=ctypes.RTLD_LOCAL)
                from ._libheif import ffi, lib  # noqa: F401
            except (OSError, ImportError) as homebrew_error:
                error = homebrew_error
            else:
                error = None
    if error is not None:
        raise ImportError(
            f'Cannot load libheif extension. {INSTALL_HINT}'
        ) from error


version_number = lib.heif_get_version_number()
libheif_version = tuple((version_number >> shift) & 255 for shift in (24, 16, 8))
if libheif_version < MIN_VERSION:
    version_string = '.'.join(map(str, libheif_version))
    raise ImportError(
        f'libheif {version_string} is older than 1.17. {INSTALL_HINT}'
    )
