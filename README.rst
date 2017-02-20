=====================================================
tango-simlib: Easily generate TANGO device simulators
=====================================================

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

 - Makes it possible to start developing the CAM system before hardware
   or vendor-provided hardware simulators are available.
 - Allows gaps in interfaces to be identified early on in the development
   process.

As development progresses, The full, actual, MeerKAT/KAT-7 CAM is run against
the simulated devices, allowing CAM functionality to be tested without the need
of real telescope hardware. The simulators also expose a back-channel that can
be used to modify the behaviour of the simulators during tests e.g. to simulate
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


Basic Usage
===========

Installation
------------

Note that installation requires the TANGO binary prerequisites to be
installed. If you cannot install the PyTango_ package you will not be able to
install `tango-simlib`.

.. _PyTango: https://pypi.python.org/pypi/PyTango


Installation from source, working dir where source is checked out

.. code-block:: bash
  
    $ pip install .

In the neare future, this package should be available on PYPI, allowing

.. code-block:: bash
  
    $ pip install tango-simlib


Simulators
==========

Generating Simulators
---------------------

Basic example of how to make use of the tango simulator generator module.
Give it a path to the description files xmi or simdd or both

.. code-block:: bash

    $ tango-simlib-tango-simulator-generator --sim-data-file Weather.xmi\
                                 --dserver-name tango_weather_xmi

Weather simulators
------------------

Example of starting the weather simulator generated from the Weather.xmi file
with a SimControl instance using tango_launcher

.. code-block:: bash

    $ tango-simlib-tango-launcher --name mkat_sim/weather/1 --class Weather\
                          --name mkat_simcontrol/weather/1\
                          --class WeatherSimControl\
                          --server-command tango-simlib-weather-xmi-DS --port 0\
                          --server-instance tango-launched\
 --put-device-property mkat_simcontrol/weather/1:model_key:mkat_sim/weather/1

Example of starting the weather simulator generated from the Weather_SIMDD.json
file with a SimControl instance using tango_launcher

.. code-block:: bash
 
    $ tango-simlib-tango-launcher --name mkat_sim/weather/2 --class Weather\
                           --name mkat_simcontrol/weather/2\
                           --class WeatherSimControl\
                           --server-command tango-simlib-weather-simdd-DS\
                           --port 0\
                           --server-instance tango-launched\
  --put-device-property mkat_simcontrol/weather/2:model_key:mkat_sim/weather/2

MeerKAT Video Display System simulator
--------------------------------------

Example of starting the VDS simulator generated from both the MkatVds.xmi and
the MkatVds_SIMDD.json files with a SimControl instance using tango_launcher

.. code-block:: bash

    $ tango-simlib-tango-launcher --name mkat_sim/vds/1 --class MkatVds\
                          --name mkat_simcontrol/vds/1\
                          --class MkatVdsSimControl\
                          --server-command tango-simlib-vds-xmi-simdd-DS\
                          --port 0\
                          --server-instance tango-launched\
 --put-device-property mkat_simcontrol/vds/1:model_key:mkat_sim/vds/1

Once the tango-simlib-tango-launcher script has been executed, the TANGO server will be created in the TANGO database. The TANGO device server will be registered along with its properties and the server process will be started. This will start the server instance which has the two classes 'Weather' and 'WeatherSimControl' registered under it, respectively. Which in turn will start thee devices from each of the TANGO classes.

Here is what you would have in your TANGO DB once your devices have been registered

.. class:: no-web

    .. image:: https://cloud.githubusercontent.com/assets/16665803/23126716/c0f366fc-f780-11e6-9b55-28ff26b834e0.png
        :alt: HTTPie compared to cURL
        :width: 30%
        :align: right
        
    .. image:: https://cloud.githubusercontent.com/assets/16665803/23127812/0ed30a54-f785-11e6-8a81-4854c2b13efd.png
        :alt: HTTPie compared to cURL
        :width: 30%
        :align: center
       
    .. image:: https://cloud.githubusercontent.com/assets/16665803/23127824/1a7d603e-f785-11e6-99c0-2e20e64624a5.png
        :alt: HTTPie compared to cURL
        :width: 30%
        :align: left
        
In this instance, we have the simulated device in an alarm state after executing the 'SetOffRainStorm' command on the test device interface, or what we call the simulator controller.

- [-] Add basic Readme

  - [X] Introduction and purpose
  - [X] Basic examples of use. I.e. just how to start up a simulator using
    pre-existing example files
  - [ ] Get/generate example simulators in an example folder

    - [ ] XMI only
    - [ ] XMI + SIMDD
    - [ ] SIMDD only

  - [ ] Screenshots of interfaces?
    - http://stackoverflow.com/questions/10189356/how-to-add-screenshot-to-readmes-in-github-repository
  - [X] Link to SIMDD working document
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
