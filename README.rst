Gridworkbench (ESA Fork)
==================
.. image:: https://img.shields.io/pypi/v/esa.svg
   :target: https://pypi.org/project/esa/
.. image:: https://img.shields.io/pypi/pyversions/esa.svg
   :target: https://pypi.org/project/esa/
.. image:: https://img.shields.io/discord/1114563747651006524
   :target: https://discord.gg/V9v8NRCT
.. image:: https://joss.theoj.org/papers/10.21105/joss.02289/status.svg
   :target: https://doi.org/10.21105/joss.02289
.. image:: https://img.shields.io/pypi/l/esa.svg
   :target: https://github.com/mzy2240/ESA/blob/master/LICENSE
.. image:: https://pepy.tech/badge/esa/month
   :target: https://pepy.tech/project/esa
.. image:: https://img.shields.io/badge/coverage-100%25-brightgreen
   :target: https://pypi.org/project/esa/

GridWorkbench is a syntax-sugar fork to make data access as easy as possible.

Easy SimAuto (ESA) is an easy-to-use Power System Analysis Automation
Platform atop PowerWorld's Simulator Automation Server (SimAuto).
ESA wraps all PowerWorld SimAuto functions, supports Auxiliary scripts,
provides helper functions to further simplify working with SimAuto and
also turbocharges with native implementation of SOTA algorithms. Wherever
possible, data is returned as Pandas DataFrames, making analysis a breeze.
ESA is well tested and fully `documented`_.

`Documentation`_
----------------

For quick-start directions, installation instructions, API reference,
examples, and more, please check out ESA's `documentation`_.

If you have your own copy of the ESA repository, you can also view the
documentation locally by navigating to the directory ``docs/html`` and
opening ``index.html`` with your web browser.


Installation
------------

For local releases you must install in edit mode. Enter the working directory and execute the following.

.. code:: bat

    python -m pip install gridwb -e .

    
License
-------

`Apache License 2.0 <https://www.apache.org/licenses/LICENSE-2.0>`__

.. _documentation: https://wyattlaundry.github.io/GridWorkBenchESA/
.. _documented: https://wyattlaundry.github.io/GridWorkBenchESA/
