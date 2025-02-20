This "quick start" example has several purposes:

*   Syntax Sugar for data accessibility.

Before running the example below, define a CASE_PATH constant (the file
path to a PowerWorld ``.pwb`` case file) like so (adapt the path as
needed for your system):

.. code:: python

    CASE = r"C:\Users\myuser\...\PWcase.pwb"

On to the quick start!

Start by Importing the SimAuto Wrapper (SAW) class:

.. code:: python

   >>> from gridwb.workbench import *


Initialize SAW instance using 14 bus test case:

.. code:: python

   >>> wb = GridWorkBench(CASE) 

Solve the power flow:

.. code:: python

   >>> wb.pflow()

This will automatically return a pandas Series with voltages.