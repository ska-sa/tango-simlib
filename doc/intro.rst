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
Description Datafile* (SimDD_). The format of this file is currently a working
proposal and subject to change. A more formal format specification is being
worked on.

Note that ``tango-simlib`` does not generate simulator code. Rather, the
simulator's behaviour is driven by the description data at run-time using *Python*'s
dynamic programming features. If the description files (XMI or SimDD) are
modified, the simulator device server only needs to be restarted for the changes
to take effect.

Rationale
---------

During the development of the control and monitoring (*CAM*) systems for the
KAT-7_ (KAT-7-wiki_) and MeerKAT_ (MeerKAT-wiki_) at SKASA_ it was found that
having control-interface simulators available for all hardware and subsystems
that *CAM* needs to control and monitor is an incredibly valuable resource. In
early *CAM* development it:

- Makes it possible to start developing the *CAM* system before hardware
  or vendor-provided hardware simulators are available.
- Allows gaps in interfaces to be identified early on in the development
  process.

As development progresses, the full, actual, *MeerKAT*/*KAT-7* *CAM* is run against
the simulated devices, allowing *CAM* functionality to be tested without the need
of real telescope hardware. The simulators also expose a back-channel that can
be used to modify the behaviour of the simulators during tests e.g. to simulate
error conditions. This is exploited by *CAM* developers in their own development
environments for day to day development tasks and also allows daily automated
functional integration tests to be run. It was also found that initially having
even a very simple simulator available is quite valuable, and that for many
devices the simple simulator is always sufficient.


The *KAT-7* and *MeerKAT* telescopes use the *Karoo Array Telescope Control Protocol*
(KATCP_) for inter-device, subsystem and component communications.
In light of that a library was developed that makes it very easy to
code a basic simulator, providing no-op command (*KATCP* request) handlers and
randomly varying attribute (*KATCP* sensor) values along with the back-channel
interface for "free".

The planned SKA_ telescope project that the SKASA_ team is participating in has
decided to standardise on the TANGO_ control systems framework. This library is
an attempt to bring the same simulation approach used for the *KAT-7* and *MeerKAT*
telescope to the *TANGO* world.


.. _TANGO: http://www.tango-controls.org/
.. _POGO: http://www.esrf.eu/computing/cs/tango/tango_doc/tools_doc/pogo_doc/
.. _SimDD: https://docs.google.com/document/d/1tkRGnKu5g8AHxVjK7UkEiukvqtqgZDzptphVCHemcIs/edit?usp=sharing
.. _KAT-7: https://www.ska.ac.za/science-engineering/kat-7/
.. _KAT-7-wiki: https://en.wikipedia.org/wiki/KAT-7
.. _MeerKAT: https://www.ska.ac.za/science-engineering/meerkat/
.. _MeerKAT-wiki: https://en.wikipedia.org/wiki/MeerKAT
.. _SKASA: http://www.ska.ac.za/
.. _KATCP: http://pythonhosted.org/katcp/
.. _SKA: https://www.skatelescope.org/
.. _CAM_Style_guide: https://docs.google.com/document/d/1aZoIyR9tz5rCWr2qJKuMTmKp2IzHlFjrCFrpDDHFypM/edit?usp=sharing
.. _PyTango: https://pypi.python.org/pypi/PyTango
.. _source: https://github.com/ska-sa/tango-simlib


===========
Basic Usage
===========

Installation
------------

Note that installation requires the *TANGO* binary prerequisites to be
installed. If you cannot install the PyTango_ package you will not be able to
install ``tango-simlib``.

Installation from source_, working directory where source is checked out

.. code-block:: bash
  
    $ pip install .

This package is available on *PYPI*, allowing

.. code-block:: bash
  
    $ pip install tango-simlib

=================
Device Simulators
=================

Generating Simulators
---------------------

The basic way of generating a *TANGO* device simulator using this library is to make use of the *TANGO* simulator generator module.
Give it a path to the description files (XMI or SimDD or both).

.. code-block:: bash

    $ tango-simlib-generator --sim-data-file Weather.xmi\
                             --dserver-name weather-DS\
                             --directory .

This will generate a python executable file in your current working directory named ``weather-DS``.

In order to run this generated device simulator code, you can execute the ``tango-launcher`` script, 
a helper script which will register the *TANGO* device server, setup any required device properties and
in turn start up the device server process, all in one go.

.. code-block:: bash

    $ tango-simlib-launcher --name mkat_sim/weather/1 --class Weather\
                            --name mkat_simcontrol/weather/1\
                            --class WeatherSimControl\
                            --server-command weather-DS --port 0\
                            --server-instance tango-launched\
                            --put-device-property mkat_simcontrol/weather/1:model_key:mkat_sim/weather/1

Ready-made Simulators
---------------------
Weather simulators
******************

A code snippet of starting the ``Weather`` simulator generated from the ``Weather.xmi`` file
with a ``SimControl`` instance using the ``tango_launcher.py`` script.
Change directory to tango_simlib/examples/

.. code-block:: bash

    $ tango-simlib-launcher --name mkat_sim/weather/1 --class Weather\
                            --name mkat_simcontrol/weather/1\
                            --class WeatherSimControl\
                            --server-command weather1.py --port 0\
                            --server-instance tango-launched\
                            --put-device-property mkat_simcontrol/weather/1:model_key:mkat_sim/weather/1

An example of starting the ``Weather`` simulator generated from the ``Weather_SimDD.json``
file with a ``SimControl`` instance using the ``tango_launcher.py`` script.

.. code-block:: bash
 
    $ tango-simlib-launcher --name mkat_sim/weather/2 --class Weather\
                            --name mkat_simcontrol/weather/2\
                            --class WeatherSimControl\
                            --server-command weather2.py --port 0\
                            --server-instance tango-launched\
                            --put-device-property mkat_simcontrol/weather/2:model_key:mkat_sim/weather/2

*MeerKAT* Video Display System simulator
****************************************

An example of starting the *VDS* simulator generated from both the ``MkatVds.xmi`` and
the ``MkatVds_SimDD.json`` files with a ``SimControl`` instance using the ``tango_launcher.py`` script.

.. code-block:: bash

    $ tango-simlib-launcher --name mkat_sim/vds/1 --class MkatVds\
                            --name mkat_simcontrol/vds/1\
                            --class MkatVdsSimControl\
                            --server-command mkat_vds.py --port 0\
                            --server-instance tango-launched\
                            --put-device-property mkat_simcontrol/vds/1:model_key:mkat_sim/vds/1


Once the ``tango-simlib-tango-launcher`` script has been executed, the *TANGO* server will be created in the *TANGO* database. The *TANGO* device server will be registered along with its properties and the server process will be started. This will start the server instance which has the two classes ``Weather`` and ``WeatherSimControl`` registered under it, respectively, which in turn will start the devices from each of the *TANGO* classes.

Screenshots of Interfaces
-------------------------

This is what you would have in the *TANGO* DB once the device server has been registered

   .. figure:: https://cloud.githubusercontent.com/assets/16665803/23232667/d322b3e8-f954-11e6-86df-942b3b7bd233.png
    :width: 60%
    :align: center
    :alt: alternate text
    :figclass: align-center

    Figure 1. A snapshot of the *TANGO* DB viewed using *JIVE* - the *TANGO*-DB browser.
    

In this instance, we have the simulated device in an alarm state after executing the *SetOffRainStorm* command on the test device interface, or what we call the simulator controller.

    .. figure:: https://cloud.githubusercontent.com/assets/16665803/23234302/5068380a-f95a-11e6-868c-9a0f3e9d1aac.png
       :width: 60%
       :align: center
       :alt: alternate text
       :figclass: align-center

       Figure 2. A view of the sim device and its associated sim control interface using the *TANGO Application ToolKit* (ATK) client framework.


