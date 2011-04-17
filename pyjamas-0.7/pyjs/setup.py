import os
from setuptools import setup, find_packages, Extension

setup(
    name="pyjs",
    version='0.1.0',
    packages=find_packages('src'),
    package_dir = {'':'src'},
    zip_safe = True,
    include_package_data = False,
    install_requires = [],
    extras_require = dict(test=['zope.testing']),
    entry_points = {'console_scripts':[
        'build=pyjs.browser:build_script',
        'translate=pyjs.translator:main',
        'smbuild=pyjs.sm:build_script',
    ]},
    )
