=====================================================================
tango-simlib: A library for easily generating TANGO device simulators
=====================================================================

Introduction
============

`tango-simlib` is a library that aids the data-driven development TANGO_ device
simulators. It aims to make it easy to develop basic simulators while making it
possible to implement more complex simulators. In addition to the simulated
device interface, a separate TANGO simulation-control interface is generated,
allowing the simulator to be manipulated via a back-channel to simulate
e.g. failure conditions on the simulated device interface.

Using only the basic TANGO interface description captured via a POGO_ generated
XMI file, a basic simulator with randomly varying attributes and no-op command
handlers can be generated with no further coding. Attribute simulation
parameters and simple command behaviour can be specified using a Simulator
Description Datafile (SIMDD_). The format of this file is currently a working
proposal and subject to change. A more formal format specification is being
worked on.

Note that `tango-simlib` does not generate simulator code. Rather, the
simulator's behaviour is driven by the description data at run-time using Python'
dynamic programming features. If the the description files (XMI or SIMDD) are
modified, the simulator device server only needs to be restarted for the changes
to take effect.

Rationale
---------

During the development of the control and monitoring (CAM) systems for the
KAT-7_ (KAT-7-wiki_) and MeerKAT_ (MeerKAT-wiki_) at SKASA_

.. _TANGO: http://www.tango-controls.org/
.. _POGO: http://www.esrf.eu/computing/cs/tango/tango_doc/tools_doc/pogo_doc/
.. _SIMDD: https://docs.google.com/document/d/1tkRGnKu5g8AHxVjK7UkEiukvqtqgZDzptphVCHemcIs/edit?usp=sharing
.. _KAT-7: https://www.ska.ac.za/science-engineering/kat-7/
.. _KAT-7-wiki: https://en.wikipedia.org/wiki/KAT-7
.. _MeerKAT: https://www.ska.ac.za/science-engineering/meerkat/
.. _MeerKAT-wiki: https://en.wikipedia.org/wiki/MeerKAT
.. _SKASA: http://www.ska.ac.za/

aims to make it easy to generate basic
simulators of devices with TANGO

- [ ] Add basic Readme
  - [ ] Introduction and purpose
  - [ ] Basic examples of use. I.e. just how to start up a simulator using
    pre-existing example files
  - [ ] Get/generate example simulators in an example folder
    - [ ] XMI only
    - [ ] XMI + SIMDD
    - [ ] SIMDD only
  - [ ] Screenshots of interfaces?
    - http://stackoverflow.com/questions/10189356/how-to-add-screenshot-to-readmes-in-github-repository
  - [ ] Link to SIMDD working document
  - [ ] Link to full documentation
  - [ ] Link to our coding standard. (If you would like to contribute, please
    attempt to follow our coding standard)
- [ ] Copy sphix toolflow from katcp
  - Or just install numpydoc package?
  - Optional deps that can be used for documentation stuff:
    - http://stackoverflow.com/questions/6237946/optional-dependencies-in-distutils-pip
    - http://peak.telecommunity.com/DevCenter/setuptools#declaring-extras-optional-features-with-their-own-dependencies
    - http://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies
- [ ] Try an do some autodoc generation
- [ ] Next? 
