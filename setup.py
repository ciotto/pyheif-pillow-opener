#!/usr/bin/env python
from setuptools import setup
import os.path

__version__ = '0.2.0'

github_url = 'https://github.com/uploadcare'
package_name = 'heif-image-plugin'
package_path = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(package_path, 'README.md')) as f:
    long_description = f.read()

setup(
    name=package_name,
    py_modules=['HeifImagePlugin'],
    version=__version__,
    description='Simple HEIF/HEIC images plugin for Pillow base on pyhief library.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Alexander Karpinsky',
    author_email='homm86@gmail.com',
    url='%s/%s' % (github_url, package_name),
    download_url='%s/%s/archive/v%s.tar.gz' % (github_url, package_name, __version__),
    keywords=['heif', 'heic', 'Pillow', 'plugin', 'pyhief'],
    install_requires=[
        "pyheif>=0.5.1",
    ],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX :: Linux",
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Multimedia :: Graphics',
    ],
    license='MIT',
    test_suite='tests',
)
