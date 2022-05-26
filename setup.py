#!/usr/bin/env python

import os

from setuptools import find_packages, setup

this_directory = os.path.abspath(os.path.dirname(__file__))

files = {"Readme": "README.rst", "Changelog": "CHANGELOG.rst"}

long_description = ""
for name, filename in files.items():
    if name != "Readme":
        header = "=" * len(name)
        long_description += "\n{}\n{}\n{}\n".format(header, name, header)
    with open(os.path.join(this_directory, filename)) as _f:
        file_contents = _f.read()
    long_description += "\n" + file_contents + "\n\n"

setup(
    name="tango_simlib",
    description="Generic library for creating simulated TANGO devices.",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="MeerKAT CAM Team",
    author_email="cam@ska.ac.za",
    packages=find_packages(),
    url="https://github.com/ska-sa/tango-simlib",
    download_url="https://pypi.python.org/pypi/tango-simlib",
    home_page="http://tango-simlib.readthedocs.io",
    license="BSD",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    platforms=["OS Independent"],
    setup_requires=["katversion"],
    use_katversion=True,
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
    install_requires=[
        "future",
        "futures; python_version<'3'",
        "pyrsistent==0.16.0; python_version<'3'",
        "pyrsistent; python_version>='3'",
        "jsonschema==3.2.0; python_version<'3'",
        "jsonschema; python_version>='3'",
        "numpy",
        "PyTango>=9.2.2",
        "pathlib",
        "pyyaml",
    ],
    tests_require=["katcp", "numpy", "mock", "nose-xunitmp", "coverage", "nose"],
    extras_require={"docs": ["sphinx-pypi-upload", "numpydoc", "Sphinx", "mock"]},
    zip_safe=False,
    include_package_data=True,
    package_data={
        "tango_simlib": [
            "utilities/SimDD.schema",
            "tests/config_files/*.xmi",
            "tests/config_files/*.json",
        ]
    },
    scripts=["scripts/DishElementMaster-DS", "scripts/Weather-DS"],
    entry_points={
        "console_scripts": [
            "tango-simlib-generator" "= tango_simlib.tango_sim_generator:main",
            "tango-simlib-launcher = tango_simlib.tango_launcher:main",
            "tango-yaml = tango_simlib.tango_yaml_tools.main:main",
        ]
    },
)
