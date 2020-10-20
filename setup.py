#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup
import os
try:
    # pip >=20
    from pip._internal.network.session import PipSession
    from pip._internal.req import parse_requirements
except ImportError:
    try:
        # 10.0.0 <= pip <= 19.3.1
        from pip._internal.download import PipSession
        from pip._internal.req import parse_requirements
    except ImportError:
        # pip <= 9.0.3
        from pip.download import PipSession
        from pip.req import parse_requirements

__version__ = '0.1.0'

github_url = 'https://github.com/ciotto'
package_name = 'pyheif-pillow-opener'
package_path = os.path.abspath(os.path.dirname(__file__))
long_description_file_path = os.path.join(package_path, 'README.md')
long_description = ''
try:
    install_requirements = [str(ir.req) for ir in parse_requirements('requirements.txt', session=PipSession())]
except AttributeError:
    install_requirements = [str(ir.requirement) for ir in parse_requirements('requirements.txt', session=PipSession())]
try:
    with open(long_description_file_path) as f:
        long_description = f.read()
except IOError:
    pass

setup(
    name=package_name,
    packages=find_packages(exclude=['docs', 'tests*']),
    include_package_data=True,
    version=__version__,
    description='pyheif-pillow-opener is a simple HEIF/HEIC opener for Pillow base on pyhief library.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Christian Bianciotto',
    author_email='info@ci8.it',
    url='%s/%s' % (github_url, package_name, ),
    download_url='%s/%s/archive/v%s.tar.gz' % (github_url, package_name, __version__, ),
    keywords=['heif', 'heic', 'Pillow'],
    install_requires=install_requirements,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
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
    test_suite='tests'
)
