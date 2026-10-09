from dataclasses import dataclass

from ._native import ffi


class HeifError(Exception):
    def __init__(self, *, code, subcode, message):
        self.code = code
        self.subcode = subcode
        self.message = message

    def __str__(self):
        return f'Code: {self.code}, Subcode: {self.subcode}, Message: "{self.message}"'


@dataclass
class LibheifError:
    code: int
    subcode: int

    def __eq__(self, e):
        if not isinstance(e, HeifError):  # pragma: no cover
            return False
        return e.code == self.code and e.subcode == self.subcode


class Errors:
    end_of_file = LibheifError(7, 100)
    unsupported_color_conversion = LibheifError(4, 3003)


def assert_success(error):
    if error.code:
        raise HeifError(
            code=error.code, subcode=error.subcode,
            message=ffi.string(error.message).decode(),
        )
