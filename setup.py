#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name="tango_simlib",
      description="Generic library for creating simulated TANGO devices.",
      author="SKA SA KAT-7 / MeerKAT CAM team",
      author_email="cam@ska.ac.za",
      packages=find_packages(),
      url='https://github.com/ska-sa/tango-simlib',
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
          "enum"],
      tests_require=[
          'enum',
          'numpy',
          'nose_xunitmp',
          'python-devicetest'],
      extras_require={
          'docs': ["sphinx-pypi-upload",
                   "numpydoc",
                   "Sphinx"],
          },
      zip_safe=False,
      include_package_data=True,
      package_data={'tango_simlib': ['tests/*.xmi', 'tests/*.json']},
      dependency_links=[
          'git+https://github.com/vxgmichel/pytango-devicetest.git#egg=python_devicetest'],
      entry_points={
          'console_scripts': [
              'tango-simlib-tango-simulator-generator'
              '= tango_simlib.tango_sim_generator:main',
              'tango-simlib-tango-launcher = tango_simlib.tango_launcher:main'
          ]}
      )
