from copy import copy
from weakref import WeakKeyDictionary

from ._native import ffi, lib


_keep_refs = WeakKeyDictionary()


class Transformations:
    # Signed permutations mapping source coordinates to EXIF orientations.
    # (a, b, c, d): x′ = a·x + b·y, y′ = c·x + d·y
    _orientations = (
        (1, 0, 0, 1),
        (1, 0, 0, 1),
        (-1, 0, 0, 1),
        (-1, 0, 0, -1),
        (1, 0, 0, -1),
        (0, 1, 1, 0),
        (0, -1, 1, 0),
        (0, -1, -1, 0),
        (0, 1, -1, 0),
    )

    def __init__(self, ispe_width, ispe_height):
        self.ispe_width = ispe_width
        self.ispe_height = ispe_height
        self.crop = (0, 0, ispe_width, ispe_height)
        self.orientation_tag = 0

    def apply_orientation(self, *, turn_ccw=0, flip_horizontal=False,
                          flip_vertical=False):
        a, b, c, d = self._orientations[self.orientation_tag]
        for _ in range(turn_ccw % 4):
            a, b, c, d = c, d, -a, -b
        if flip_horizontal:
            a, b = -a, -b
        if flip_vertical:
            c, d = -c, -d
        self.orientation_tag = self._orientations.index((a, b, c, d), 1)

    def apply_crop(self, left, top, width, height):
        a, b, c, d = self._orientations[self.orientation_tag]
        origin_x = min(0, a * self.ispe_width) + min(0, b * self.ispe_height)
        origin_y = min(0, c * self.ispe_width) + min(0, d * self.ispe_height)
        x1 = a * (left + origin_x) + c * (top + origin_y)
        y1 = b * (left + origin_x) + d * (top + origin_y)
        x2 = x1 + a * width + c * height
        y2 = y1 + b * width + d * height
        left = max(0, min(self.ispe_width - 1, min(x1, x2)))
        top = max(0, min(self.ispe_height - 1, min(y1, y2)))
        width = max(0, min(self.ispe_width - left, abs(x2 - x1)))
        height = max(0, min(self.ispe_height - top, abs(y2 - y1)))
        self.crop = (left, top, width, height)

    def __eq__(self, other):
        return (self.crop == other.crop
                and self.orientation_tag == other.orientation_tag)


def read_transformations(context, handle):
    transforms = Transformations(
        lib.heif_image_handle_get_ispe_width(handle),
        lib.heif_image_handle_get_ispe_height(handle),
    )
    item = lib.heif_image_handle_get_item_id(handle)
    count = lib.heif_item_get_transformation_properties(context, item, ffi.NULL, 0)
    properties = ffi.new('heif_property_id[]', count)
    count = lib.heif_item_get_transformation_properties(
        context, item, properties, count,
    )
    for prop in properties[0:count]:
        kind = lib.heif_item_get_property_type(context, item, prop)
        if kind == lib.heif_item_property_type_transform_mirror:
            direction = lib.heif_item_get_property_transform_mirror(context, item, prop)
            horizontal = direction == lib.heif_transform_mirror_direction_horizontal
            transforms.apply_orientation(
                flip_horizontal=horizontal, flip_vertical=not horizontal,
            )
        elif kind == lib.heif_item_property_type_transform_rotation:
            angle = lib.heif_item_get_property_transform_rotation_ccw(
                context, item, prop,
            )
            transforms.apply_orientation(turn_ccw=angle // 90)
        elif kind == lib.heif_item_property_type_transform_crop:
            borders = ffi.new('int[4]')
            lib.heif_item_get_property_transform_crop_borders(
                context, item, prop, transforms.ispe_width, transforms.ispe_height,
                borders, borders + 1, borders + 2, borders + 3,
            )
            transforms.apply_crop(
                borders[0], borders[1],
                transforms.ispe_width - borders[0] - borders[2],
                transforms.ispe_height - borders[1] - borders[3],
            )
    return transforms


def crop_heif_file(heif):
    # Zero-copy crop before loading. Just shifts data pointer and updates meta.
    crop = heif.transformations.crop
    if crop == (0, 0) + heif.size:
        return heif

    if heif.mode not in ("L", "RGB", "RGBA"):  # pragma: no cover
        raise ValueError("Unknown mode")
    pixel_size = len(heif.mode)

    offset = heif.stride * crop[1] + pixel_size * crop[0]
    cdata = ffi.from_buffer(heif.data, require_writable=False) + offset
    # The final cropped row may end before the original stride does.
    data = ffi.buffer(cdata, min(len(heif.data) - offset, heif.stride * crop[3]))

    # Pointer arithmetic drops the reference held by ffi.from_buffer.
    _keep_refs[cdata] = heif.data

    new_heif = copy(heif)
    new_heif.size = crop[2:4]
    new_heif.transformations = copy(heif.transformations)
    new_heif.transformations.crop = (0, 0) + crop[2:4]
    new_heif.data = data
    return new_heif
