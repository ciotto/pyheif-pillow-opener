import atexit

from ._native import ffi, lib
from .errors import assert_success
from .metadata import read_color_profile, read_metadata
from .transformations import read_transformations


assert_success(lib.heif_init(ffi.NULL))
atexit.register(lib.heif_deinit)


def _keep_alive(release, *refs):
    def callback(pointer):
        release(pointer)
    callback._refs = refs
    return callback


class HeifImage:
    def __init__(self, context, handle, *, apply_transformations):
        self._context = context
        self._handle = handle
        self.apply_transformations = apply_transformations
        if apply_transformations:
            self.size = (lib.heif_image_handle_get_width(handle),
                         lib.heif_image_handle_get_height(handle))
        else:
            self.size = (lib.heif_image_handle_get_ispe_width(handle),
                         lib.heif_image_handle_get_ispe_height(handle))
        self.has_alpha = bool(lib.heif_image_handle_has_alpha_channel(handle))
        self.mode = 'RGBA' if self.has_alpha else 'RGB'
        self.bit_depth = lib.heif_image_handle_get_luma_bits_per_pixel(handle)
        self.transformations = read_transformations(context, handle)
        self.metadata = read_metadata(handle)
        self.color_profile = read_color_profile(handle)
        self.exif = None
        self.data = None
        self.stride = None

    def load(self, *, strict_decoding: bool = True) -> 'HeifImage':
        if self._handle is None:
            return self
        options = ffi.gc(lib.heif_decoding_options_alloc(),
                         lib.heif_decoding_options_free)
        options.ignore_transformations = int(not self.apply_transformations)
        options.convert_hdr_to_8bit = 1
        options.strict_decoding = int(strict_decoding)
        chroma = (lib.heif_chroma_interleaved_RGBA if self.has_alpha
                  else lib.heif_chroma_interleaved_RGB)
        out = ffi.new('struct heif_image **')
        image = None
        try:
            assert_success(lib.heif_decode_image(
                self._handle, out, lib.heif_colorspace_RGB, chroma, options,
            ))
            image = ffi.gc(out[0], lib.heif_image_release)
            stride = ffi.new('int *')
            plane = lib.heif_image_get_plane_readonly(
                image, lib.heif_channel_interleaved, stride,
            )
            plane = ffi.gc(plane, _keep_alive(lambda pointer: None, image),
                           size=stride[0] * self.size[1])
            self.stride = stride[0]
            self.data = ffi.buffer(plane, self.stride * self.size[1])
        finally:
            # A decoder can return an allocated image alongside an error.
            if out[0] != ffi.NULL and image is None:
                lib.heif_image_release(out[0])
            self.close()
        return self

    def close(self) -> None:
        if self._handle is not None:
            ffi.release(self._handle)
        if self._context is not None:
            ffi.release(self._context)
        self._handle = None
        self._context = None


def open(data: bytes, *, apply_transformations: bool = True) -> HeifImage:
    context = ffi.gc(lib.heif_context_alloc(),
                     _keep_alive(lib.heif_context_free, data), size=len(data))
    out = ffi.new('struct heif_image_handle **')
    handle = None
    try:
        assert_success(lib.heif_context_read_from_memory_without_copy(
            context, data, len(data), ffi.NULL,
        ))
        assert_success(lib.heif_context_get_primary_image_handle(context, out))
        handle = ffi.gc(out[0], _keep_alive(lib.heif_image_handle_release, context))
        return HeifImage(context, handle, apply_transformations=apply_transformations)
    except Exception:
        if handle is not None:
            ffi.release(handle)
        elif out[0] != ffi.NULL:
            lib.heif_image_handle_release(out[0])
        ffi.release(context)
        raise


def check(data: bytes) -> bool:
    return lib.heif_check_filetype(data, len(data)) != lib.heif_filetype_no
