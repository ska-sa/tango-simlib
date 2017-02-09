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
KAT-7_ (KAT-7-wiki_) and MeerKAT_ (MeerKAT-wiki_) at SKASA_ it was found that
having control-interface simulators available for all hardware and subsystems
that CAM needs to control and monitor is an incredibly valuable resource. In
early CAM development it:

 - Makes it possible to start devloping the CAM system before hardware
   or vendor-provided hardware simulators are available.
 - Allows gaps to in interfaces to be identified early on in the development
   process.

As development progresses, The full, actual, MeerKAT/KAT-7 CAM is run against
the simulated devices, allowing CAM functionality to be tested without the need
of real telescope hardware. The simulators also expose a back-channel that can
be using to modify the behaviour of the simulators during tests to e.g. simulate
error conditions. This is exploited by CAM developers in their own development
environments for day to day development tasks and also allows daily automated
functional integration tests to be run. It was also found that initially having
even a very simple simulator available is quite valuable, and that for many
devices the simple simulator is always sufficient.


The KAT-7 and MeerKAT telescopes use the Karoo Array Telescope Control Protocol
KATCP_ for inter-device, subsystem and component communications. 
In light of that a library was developed that makes it very easy to
code a basic simulator, providing no-op command (KATCP request) handlers and
randomly varying attribute (KATCP sensor) values along with the back-channel
interface for "free".

The planned SKA_ telescope project that the SKASA_ team is participating in has
decided to standardise on the TANGO_ control systems framework. This library is
an attempt to bring the same simulation approach used for the KAT-7 and MeerKAT
telescope to the TANGO world.


.. _TANGO: http://www.tango-controls.org/
.. _POGO: http://www.esrf.eu/computing/cs/tango/tango_doc/tools_doc/pogo_doc/
.. _SIMDD: https://docs.google.com/document/d/1tkRGnKu5g8AHxVjK7UkEiukvqtqgZDzptphVCHemcIs/edit?usp=sharing
.. _KAT-7: https://www.ska.ac.za/science-engineering/kat-7/
.. _KAT-7-wiki: https://en.wikipedia.org/wiki/KAT-7
.. _MeerKAT: https://www.ska.ac.za/science-engineering/meerkat/
.. _MeerKAT-wiki: https://en.wikipedia.org/wiki/MeerKAT
.. _SKASA: http://www.ska.ac.za/
.. _KATCP: http://pythonhosted.org/katcp/
.. _SKA: https://www.skatelescope.org/

aims to make it easy to generate basic
simulators of devices with TANGO

- [ ] Add basic Readme
  - [X] Introduction and purpose
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
