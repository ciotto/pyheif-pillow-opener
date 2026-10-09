import subprocess
import sys
from pathlib import Path

import pytest

import _heif_image_plugin


@pytest.mark.parametrize('local_extension', [False, True])
@pytest.mark.parametrize('extend_path_value', [None, '0', '1'])
def test_extension_search_requires_opt_in_and_keeps_local_priority(
        tmp_path, monkeypatch, local_extension, extend_path_value):
    if extend_path_value is None:
        monkeypatch.delenv('HEIF_IMAGE_PLUGIN_EXTEND_PATH', raising=False)
    else:
        monkeypatch.setenv('HEIF_IMAGE_PLUGIN_EXTEND_PATH', extend_path_value)
    local = tmp_path / 'local' / '_heif_image_plugin'
    installed = tmp_path / 'installed' / '_heif_image_plugin'
    local.mkdir(parents=True)
    installed.mkdir(parents=True)
    local.joinpath('__init__.py').write_text(
        Path(_heif_image_plugin.__file__).read_text())
    local.joinpath('reader.py').write_text('source = "local"')
    installed.joinpath('__init__.py').write_text(
        'raise AssertionError("installed initializer must not run")')
    installed.joinpath('reader.py').write_text('source = "installed"')
    installed.joinpath('_libheif.py').write_text('source = "installed"')
    if local_extension:
        local.joinpath('_libheif.py').write_text('source = "local"')

    result = subprocess.run(
        [sys.executable, '-c',
         'import sys; sys.path[:0] = sys.argv[1:]; '
         'from _heif_image_plugin import reader, _libheif; '
         'print(reader.source, _libheif.source)',
         str(local.parent), str(installed.parent)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    if not local_extension and extend_path_value != '1':
        assert result.returncode != 0
        assert "cannot import name '_libheif'" in result.stderr
        return
    assert result.returncode == 0, result.stderr
    expected_extension = 'local' if local_extension else 'installed'
    assert result.stdout.strip() == f'local {expected_extension}'
