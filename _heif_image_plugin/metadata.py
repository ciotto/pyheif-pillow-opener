from copy import copy

import piexif

from ._native import ffi, lib
from .errors import assert_success


def read_metadata(handle):
    count = lib.heif_image_handle_get_number_of_metadata_blocks(handle, ffi.NULL)
    if not count:
        return None
    ids = ffi.new('heif_item_id[]', count)
    count = lib.heif_image_handle_get_list_of_metadata_block_IDs(
        handle, ffi.NULL, ids, count,
    )
    metadata = []
    for item in ids[0:count]:
        kind = ffi.string(
            lib.heif_image_handle_get_metadata_type(handle, item)
        ).decode()
        size = lib.heif_image_handle_get_metadata_size(handle, item)
        buffer = ffi.new('char[]', size)
        assert_success(lib.heif_image_handle_get_metadata(handle, item, buffer))
        data = bytes(ffi.buffer(buffer, size))
        if kind == 'Exif':
            data = data[4:]
        metadata.append({'type': kind, 'data': data})
    return metadata


def read_color_profile(handle):
    kind = lib.heif_image_handle_get_color_profile_type(handle)
    if kind not in (lib.heif_color_profile_type_rICC, lib.heif_color_profile_type_prof):
        return None
    size = lib.heif_image_handle_get_raw_color_profile_size(handle)
    buffer = ffi.new('char[]', size)
    assert_success(lib.heif_image_handle_get_raw_color_profile(handle, buffer))
    return {
        'type': 'rICC' if kind == lib.heif_color_profile_type_rICC else 'prof',
        'data': bytes(ffi.buffer(buffer, size)),
    }


def rotate_heif_file(heif):
    """
    Heif files already contain transformation chunks imir and irot which are
    dominate over Orientation tag in EXIF.

    This is not aligned with other formats behavior and we MUST fix EXIF after
    loading to prevent unexpected rotation after re-saving in other formats.

    And we come up to there is no reasons to force rotation of HEIF images
    after loading since we need update EXIF anyway.
    """
    orientation = heif.transformations.orientation_tag
    if not (1 <= orientation <= 8):
        return heif

    exif = {'0th': {piexif.ImageIFD.Orientation: orientation}}
    if heif.exif:
        try:
            exif = piexif.load(heif.exif)
            exif['0th'][piexif.ImageIFD.Orientation] = orientation
        except Exception:
            pass

    new_heif = copy(heif)
    new_heif.transformations = copy(heif.transformations)
    new_heif.transformations.orientation_tag = 0
    new_heif.exif = piexif.dump(exif)
    return new_heif


def extract_heif_exif(heif_file):
    """
    Unlike other helper functions, this alters heif_file in-place.
    """
    heif_file.exif = None

    clean_metadata = []
    for item in heif_file.metadata or []:
        if item['type'] == 'Exif':
            if heif_file.exif is None:
                if item['data'] and item['data'][0:4] == b"Exif":
                    heif_file.exif = item['data']
        else:
            clean_metadata.append(item)
    heif_file.metadata = clean_metadata
