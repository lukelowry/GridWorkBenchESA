This simple example showing how to access power world data using a numpy inspired indexing notation.

If you want to follow along, you'll first need to define your own
``CASE_PATH`` constant (the file path to a PowerWorld ``.pwb`` case
file), like so (adapt the path for your system):

.. code:: python

    >>> wb = GridWorkBench(CASE) 

Retrieve Buses:

.. code:: python

    >>> wb[Bus]

Retrieve Buses and all fields:

.. code:: python

    >>> wb[Bus, :]


Retrieve Specific Field:

.. code:: python

    >>> wb[Bus, "BusAngle"]

Retrieve Specific Fields:

.. code:: python

    >>> wb[Bus, ["BusAngle", "SubNum"]]