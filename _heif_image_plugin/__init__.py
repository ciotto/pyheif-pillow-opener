"""Internal libheif bindings for HeifImagePlugin."""

import os


# Let local Python sources use the native extension installed in site-packages.
if os.environ.get('HEIF_IMAGE_PLUGIN_EXTEND_PATH') == '1':
    from pkgutil import extend_path
    __path__ = extend_path(__path__, __name__)
