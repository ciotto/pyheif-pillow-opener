import builtins
import ctypes
import gc
import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from PIL import Image, ImageFile

import HeifImagePlugin
from _heif_image_plugin import _native, reader
from _heif_image_plugin.errors import HeifError
from _heif_image_plugin.transformations import crop_heif_file

from . import respath


@pytest.fixture
def bundled(tmp_path, monkeypatch):
    encoder = str(tmp_path / 'native-encoder')
    module = SimpleNamespace(
        get_version=mock.Mock(return_value=(1, 23, 6)),
        get_version_str=mock.Mock(return_value='1.23.6'),
        get_executable=mock.Mock(return_value=encoder),
        load_library=mock.Mock(),
    )
    monkeypatch.setitem(sys.modules, 'libheif_binary', module)
    return module, encoder


@pytest.fixture
def system(monkeypatch):
    handle = mock.Mock()
    monkeypatch.setattr(ctypes, 'CDLL', mock.Mock(return_value=handle))
    return handle


@pytest.fixture
def import_native(monkeypatch):
    original_import = builtins.__import__
    extension = SimpleNamespace(
        ffi=mock.Mock(),
        lib=SimpleNamespace(
            heif_get_version_number=mock.Mock(return_value=0x01170000)),
    )
    extension_import = mock.Mock(return_value=extension)

    def intercept(name, *args, **kwargs):
        if name == '_libheif':
            return extension_import()
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', intercept)

    def execute():
        namespace = {'__package__': '_heif_image_plugin'}
        source = Path(_native.__file__).read_text()
        exec(compile(source, _native.__file__, 'exec'), namespace)
        return namespace

    return execute, extension_import, extension


def test_bundled_library_and_native_encoder(bundled, system):
    module, expected_encoder = bundled
    handle, encoder = _native._load_bundled_library()
    assert handle is module.load_library.return_value
    assert encoder == expected_encoder
    assert Path(encoder).is_absolute()
    module.load_library.assert_called_once_with()
    module.get_version.assert_not_called()
    module.get_version_str.assert_not_called()
    module.get_executable.assert_called_once_with('heif-enc')
    ctypes.CDLL.assert_not_called()


def test_bundled_version_api_is_not_required(bundled, system):
    module, encoder = bundled
    del module.get_version
    del module.get_version_str
    assert _native._load_bundled_library() == (
        module.load_library.return_value, encoder)


def test_bundled_encoder_error_warns_before_loading(bundled, system):
    module, _ = bundled
    module.get_executable.side_effect = OSError('missing encoder')
    with pytest.warns(RuntimeWarning, match='missing encoder'):
        assert _native._load_bundled_library() == (None, 'heif-enc')
    module.load_library.assert_not_called()


def test_bundled_load_error_warns_and_uses_system(bundled, system):
    module, _ = bundled
    module.load_library.side_effect = OSError('broken bundle')
    with pytest.warns(RuntimeWarning, match='broken bundle'):
        assert _native._load_bundled_library() == (None, 'heif-enc')
    ctypes.CDLL.assert_not_called()


def test_absent_bundle_imports_system_without_preloading(
        monkeypatch, system, import_native):
    monkeypatch.setitem(sys.modules, 'libheif_binary', None)
    execute, extension_import, _ = import_native
    namespace = execute()
    assert namespace['HEIF_ENC_BIN'] == 'heif-enc'
    assert namespace['_library_handle'] is None
    extension_import.assert_called_once_with()
    ctypes.CDLL.assert_not_called()


@pytest.mark.parametrize('bundled_library', [False, True])
@pytest.mark.parametrize('version', [0x01100200, 0x01110000, 0x01170000])
def test_loaded_extension_version_is_checked(
        monkeypatch, bundled, system, import_native, bundled_library, version):
    module, _ = bundled
    if not bundled_library:
        monkeypatch.setitem(sys.modules, 'libheif_binary', None)
    execute, extension_import, extension = import_native
    extension.lib.heif_get_version_number.return_value = version
    if version < 0x01110000:
        with pytest.raises(ImportError, match=r'1\.16\.2.*libheif-binary>=1\.17'):
            execute()
    else:
        namespace = execute()
        assert namespace['libheif_version'] == tuple(
            (version >> shift) & 255 for shift in (24, 16, 8))
    extension_import.assert_called_once_with()
    module.get_version.assert_not_called()
    module.get_version_str.assert_not_called()
    if bundled_library:
        module.load_library.assert_called_once_with()
    ctypes.CDLL.assert_not_called()


@pytest.mark.parametrize('platform, library_exists', [
    ('darwin', False), ('linux', False), ('linux', True),
])
def test_unresolved_import_adds_hint_and_preserves_cause_without_fallback(
        monkeypatch, system, import_native, tmp_path, platform, library_exists):
    monkeypatch.setitem(sys.modules, 'libheif_binary', None)
    monkeypatch.setattr(sys, 'platform', platform)
    monkeypatch.setenv('HOMEBREW_PREFIX', str(tmp_path))
    if library_exists:
        library = tmp_path / 'lib' / 'libheif.dylib'
        library.parent.mkdir()
        library.touch()
    execute, extension_import, _ = import_native
    error = ImportError('missing dependency')
    extension_import.side_effect = error
    with pytest.raises(ImportError, match='libheif-binary>=1.17') as caught:
        execute()
    assert caught.value.__cause__ is error
    ctypes.CDLL.assert_not_called()


@pytest.mark.parametrize('failure', [None, 'load', 'import'])
def test_homebrew_fallback_loads_locally_after_failed_import(
        monkeypatch, system, import_native, tmp_path, failure):
    monkeypatch.setitem(sys.modules, 'libheif_binary', None)
    monkeypatch.setattr(sys, 'platform', 'darwin')
    monkeypatch.setenv('HOMEBREW_PREFIX', str(tmp_path))
    library = tmp_path / 'lib' / 'libheif.dylib'
    library.parent.mkdir()
    library.touch()
    execute, extension_import, extension = import_native
    error = OSError('broken library') if failure == 'load' else ImportError(
        'unresolved dependency')
    extension_import.side_effect = [ImportError('first import'),
                                    error if failure == 'import' else extension]

    def load(*args, **kwargs):
        assert extension_import.call_count == 1
        if failure == 'load':
            raise error
        return system

    ctypes.CDLL.side_effect = load
    if failure:
        with pytest.raises(ImportError, match='libheif-binary>=1.17') as caught:
            execute()
        assert caught.value.__cause__ is error
    else:
        namespace = execute()
        assert namespace['_library_handle'] is system
        assert namespace['libheif_version'] == (1, 23, 0)
        assert extension_import.call_count == 2
    ctypes.CDLL.assert_called_once_with(str(library), mode=ctypes.RTLD_LOCAL)


def test_encoder_override_reaches_subprocess():
    with mock.patch('HeifImagePlugin.HEIF_ENC_BIN', '/custom/heif-enc'):
        with mock.patch('HeifImagePlugin.subprocess.Popen',
                        side_effect=FileNotFoundError) as enc:
            with pytest.raises(FileNotFoundError):
                Image.new('RGB', (1, 1)).save(BytesIO(), 'HEIF')
    assert enc.call_args.args[0][0] == '/custom/heif-enc'


@pytest.fixture
def native_spy(monkeypatch):
    attributes = {}
    for name in dir(reader.lib):
        if not name.startswith('_'):
            value = getattr(reader.lib, name)
            attributes[name] = mock.Mock(wraps=value) if callable(value) else value
    proxy = SimpleNamespace(**attributes)
    monkeypatch.setattr(reader, 'lib', proxy)
    return proxy


def test_reader_decodes_lazily_and_only_once(native_spy):
    image = reader.open(Path(respath('test2.heic')).read_bytes(),
                        apply_transformations=False)
    assert image.size == (1280, 720)
    assert image.data is None
    native_spy.heif_decode_image.assert_not_called()
    assert image.load() is image
    pixels = bytes(image.data)
    assert image.load() is image
    assert bytes(image.data) == pixels
    native_spy.heif_decode_image.assert_called_once()


def test_pixel_buffer_survives_reader_and_crop_collection():
    image = reader.open(Path(respath('test2.heic')).read_bytes(),
                        apply_transformations=False).load()
    image.transformations.crop = (99, 33, 512, 256)
    cropped = crop_heif_file(image)
    data = cropped.data
    expected = bytes(data)
    image.close()
    del cropped, image
    gc.collect()
    assert bytes(data) == expected


def test_crop_at_bottom_edge_stays_within_buffer():
    image = reader.open(Path(respath('test2.heic')).read_bytes(),
                        apply_transformations=False).load()
    image.transformations.crop = (99, 719, 512, 1)
    cropped = crop_heif_file(image)
    offset = 719 * image.stride + 99 * 3
    assert bytes(cropped.data) == bytes(image.data)[offset:]
    expected = Image.frombytes(
        'RGB', image.size, image.data, 'raw', ('RGB', image.stride))
    actual = Image.frombytes(
        'RGB', cropped.size, cropped.data, 'raw', ('RGB', cropped.stride))
    assert actual == expected.crop((99, 719, 611, 720))


def test_open_error_releases_context(native_spy):
    with pytest.raises(HeifError):
        reader.open(b'not a HEIF file')
    native_spy.heif_context_free.assert_called_once()


def test_decode_error_releases_image_handle_and_context(native_spy):
    message = reader.ffi.new('char[]', b'decode failure')
    error = reader.ffi.new('struct heif_error *', {
        'code': 7, 'subcode': 100, 'message': message,
    })

    def fail_after_allocating(*args):
        result = _native.lib.heif_decode_image(*args)
        assert result.code == 0
        return error[0]

    native_spy.heif_decode_image.side_effect = fail_after_allocating
    image = reader.open(Path(respath('test2.heic')).read_bytes())
    with pytest.raises(HeifError, match='decode failure'):
        image.load()
    assert image.data is None
    native_spy.heif_image_release.assert_called_once()
    native_spy.heif_image_handle_release.assert_called_once()
    native_spy.heif_context_free.assert_called_once()


def test_strict_decoding_uses_flag_at_load_time(monkeypatch, native_spy):
    strict_values = []

    def decode(*args):
        strict_values.append(args[-1].strict_decoding)
        return _native.lib.heif_decode_image(*args)

    native_spy.heif_decode_image.side_effect = decode
    image = Image.open(respath('test2.heic'))
    monkeypatch.setattr(ImageFile, 'LOAD_TRUNCATED_IMAGES', True)
    image.load()
    assert strict_values == [0]
    monkeypatch.setattr(ImageFile, 'LOAD_TRUNCATED_IMAGES', False)
    Image.open(respath('test2.heic')).load()
    assert strict_values == [0, 1]


def test_error_fields_and_string_are_preserved():
    error = HeifError(code=7, subcode=100, message='End of file')
    assert (error.code, error.subcode, error.message) == (7, 100, 'End of file')
    assert str(error) == 'Code: 7, Subcode: 100, Message: "End of file"'
    assert error == HeifImagePlugin.Errors.end_of_file
