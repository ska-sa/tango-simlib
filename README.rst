=======================================================
tango-simlib: Easily generate *TANGO* device simulators
=======================================================

============
Introduction
============

``tango-simlib`` is a library that aids the data-driven development of TANGO_ device
simulators. It aims to make it easy to develop basic simulators while making it
possible to implement more complex simulators. In addition to the simulated
device interface, a separate *TANGO* simulation-control interface is generated,
allowing the simulator to be manipulated via a back-channel to simulate
e.g. failure conditions on the simulated device interface.

Using only the basic *TANGO* interface description captured via a POGO_ generated
XMI file, a basic simulator with randomly varying attributes and no-op command
handlers can be generated with no further coding. Attribute simulation
parameters and simple command behaviour can be specified using a *Simulator
Description Datafile* (SIMDD_). The format of this file is currently a working
proposal and subject to change. A more formal format specification is being
worked on.

Note that ``tango-simlib`` does not generate simulator code. Rather, the
simulator's behaviour is driven by the description data at run-time using *Python*'s
dynamic programming features. If the description files (XMI or SIMDD) are
modified, the simulator device server only needs to be restarted for the changes
to take effect.

.. _TANGO: http://www.tango-controls.org/
.. _POGO: http://www.esrf.eu/computing/cs/tango/tango_doc/tools_doc/pogo_doc/
.. _SIMDD: https://docs.google.com/document/d/1tkRGnKu5g8AHxVjK7UkEiukvqtqgZDzptphVCHemcIs/edit?usp=sharing
.. _CAM_Style_guide: https://docs.google.com/document/d/1aZoIyR9tz5rCWr2qJKuMTmKp2IzHlFjrCFrpDDHFypM/edit?usp=sharing
.. _PyTango: https://pypi.python.org/pypi/PyTango
.. _source: https://github.com/ska-sa/tango-simlib
.. _Documentation: http://tango-simlib.rtfd.io

===========
Basic Usage
===========

Installation
------------

Note that installation requires the *TANGO* binary prerequisites to be
installed. If you cannot install the PyTango_ package you will not be able to
install ``tango-simlib``. For more, Documentation_.

Installation from source_, working directory where source is checked out

.. code-block:: bash
  
    $ pip install .

This package is available on *PYPI*, allowing

.. code-block:: bash
  
    $ pip install tango-simlib

=======
License
=======

This project is licensed under the BSD 3-Clause License - see https://opensource.org/licenses/BSD-3-Clause for details.

==========
Contribute
==========

Contributions are always welcome! Please ensure that you adhere to our coding standards CAM_Style_guide_.
