import runpy
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import cffi
import pytest


BUILD_SCRIPT = Path(__file__).resolve().parents[1] / 'bindings' / 'build.py'


def test_build_uses_bundled_configuration(monkeypatch):
    config = {
        'include_dirs': ['/bundled/headers'],
        'library_dirs': ['/bundled/libraries'],
        'libraries': ['heif.1.17.6'],
    }
    bundled = SimpleNamespace(get_build_config=mock.Mock(return_value=config))
    monkeypatch.setitem(sys.modules, 'libheif_binary', bundled)
    builder = mock.Mock()
    monkeypatch.setattr(cffi, 'FFI', mock.Mock(return_value=builder))
    runpy.run_path(str(BUILD_SCRIPT))
    assert builder.set_source.call_args.kwargs == config
    bundled.get_build_config.assert_called_once_with()


def test_build_without_bundle_uses_standard_library_search(monkeypatch):
    monkeypatch.setitem(sys.modules, 'libheif_binary', None)
    builder = mock.Mock()
    monkeypatch.setattr(cffi, 'FFI', mock.Mock(return_value=builder))
    runpy.run_path(str(BUILD_SCRIPT))
    assert builder.set_source.call_args.kwargs == {'libraries': ['heif']}


def test_build_does_not_hide_bundled_configuration_errors(monkeypatch):
    bundled = SimpleNamespace(
        get_build_config=mock.Mock(side_effect=OSError('missing bundled library')),
    )
    monkeypatch.setitem(sys.modules, 'libheif_binary', bundled)
    with pytest.raises(OSError, match='missing bundled library'):
        runpy.run_path(str(BUILD_SCRIPT))
