This simple example showing how to access power world data using a numpy inspired indexing notation.

If you want to follow along, you'll first need to define your own
``CASE_PATH`` constant (the file path to a PowerWorld ``.pwb`` case
file), like so (adapt the path for your system):

.. code:: python

    >>> wb = GridWorkBench(CASE) 

Retrieve key fields for loads:

.. code:: python

    >>> wb[Bus]
