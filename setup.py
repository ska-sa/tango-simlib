#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name="tango_simlib",
      description="Generic library for creating simulated TANGO devices.",
      author="SKA SA KAT-7 / MeerKAT CAM team",
      author_email="cam@ska.ac.za",
      packages=find_packages(),
      url='https://github.com/ska-sa/tango-simlib',
      download_url='https://pypi.python.org/pypi/tango-simlib',
      home_page='http://tango-simlib.readthedocs.io',
      license="BSD",
      classifiers=[
          "Intended Audience :: Developers",
          "Programming Language :: Python :: 2",
          "Topic :: Software Development :: Libraries :: Python Modules",
          # TODO something for control systems?,
      ],
      platforms=["OS Independent"],
      setup_requires=["katversion"],
      use_katversion=True,
      install_requires=[
          "PyTango>=9.2.0",
          "numpy",
          "jsonschema",
          "enum"],
      tests_require=[
          'enum',
          'numpy',
          'nose_xunitmp'],
      extras_require={
          'docs': ["sphinx-pypi-upload",
                   "numpydoc",
                   "Sphinx"],
          },
      zip_safe=False,
      include_package_data=True,
      package_data={'tango_simlib': ['utilities/SIMDD.schema',
                                     'tests/config_files/*.xmi',
                                     'tests/config_files/*.json']},
      scripts=['scripts/DishElementMaster-DS',
               'scripts/Weather-DS'],
      entry_points={
          'console_scripts': [
              'tango-simlib-generator'
              '= tango_simlib.tango_sim_generator:main',
              'tango-simlib-launcher = tango_simlib.tango_launcher:main'
          ]}
      )
