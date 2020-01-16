=======================================================
tango-simlib: Easily generate *TANGO* device simulators
=======================================================

|Doc Status|
|Pypi Version|
|Python Versions|

Main website: http://tango-simlib.readthedocs.io

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
Description Datafile* (SimDD_). The format of this file is currently a working
proposal and subject to change. A more formal format specification is being
worked on.

Note that ``tango-simlib`` does not generate simulator code. Rather, the
simulator's behaviour is driven by the description data at run-time using *Python*'s
dynamic programming features. If the description files (XMI or SimDD) are
modified, the simulator device server only needs to be restarted for the changes
to take effect.

.. |Doc Status| image:: https://readthedocs.org/projects/tango-simlib/badge/?version=latest
                :target: http://tango-simlib.readthedocs.io/en/latest
                :alt:

.. |Pypi Version| image:: https://img.shields.io/pypi/v/tango-simlib.svg
                  :target: https://pypi.python.org/pypi/tango-simlib
                  :alt:

.. |Python Versions| image:: https://img.shields.io/pypi/pyversions/tango-simlib.svg
                     :target: https://pypi.python.org/pypi/tango-simlib/
                     :alt:

.. _TANGO: http://www.tango-controls.org/
.. _POGO: http://www.esrf.eu/computing/cs/tango/tango_doc/tools_doc/pogo_doc/
.. _SimDD: https://docs.google.com/document/d/1tkRGnKu5g8AHxVjK7UkEiukvqtqgZDzptphVCHemcIs/edit?usp=sharing
.. _CAM_Style_guide: https://docs.google.com/document/d/1aZoIyR9tz5rCWr2qJKuMTmKp2IzHlFjrCFrpDDHFypM/edit?usp=sharing
.. _PyTango: https://pypi.python.org/pypi/PyTango
.. _source: https://github.com/ska-sa/tango-simlib
.. _documentation: http://tango-simlib.rtfd.io
.. _license: https://github.com/ska-sa/tango-simlib/blob/master/LICENSE.txt

===========
Basic Usage
===========

Installation
------------

**Please Note**

- *tango-simlib is compatible with Python2.7 and Python>3.4*

- *Installation requires the `TANGO binary <https://tango-controls.readthedocs.io/en/latest/installation/binary_package.html>` prerequisites to be installed.*


.. code-block:: bash
    sudo apt-get install -y --no-install-recommends $(grep -vE "^\s*#" apt-build-requirements.txt | tr "\n" " ")


If you cannot install the PyTango_ package you will not be able to
install ``tango-simlib``. For more, documentation_.

Installation from source_, working directory where source is checked out

.. code-block:: bash

    $ pythonX -m pip install . # Where 'x' is the version of Python

This package is available on *PYPI*, allowing

.. code-block:: bash

    $ pip install tango-simlib

Documentation
-------------

Check out the documentation_ for more information.
Download Manual: https://media.readthedocs.org/pdf/tango-simlib/latest/tango-simlib.pdf

=======
License
=======

This project is licensed under the BSD 3-Clause License - see license_ for details.

==========
Contribute
==========

Contributions are always welcome! Please ensure that you adhere to our coding standards CAM_Style_guide_.
