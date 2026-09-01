Getting Started
===============

.. image:: https://img.shields.io/badge/License-Apache%202.0-blue.svg
   :target: https://opensource.org/licenses/Apache-2.0
   :alt: License

.. image:: https://img.shields.io/badge/python-3.9%2B-blue.svg
   :target: https://www.python.org/downloads/
   :alt: Python 3.9+

.. image:: https://img.shields.io/badge/docs-Read%20the%20Docs-blue.svg
   :target: https://esapp.readthedocs.io/
   :alt: Documentation

ESA++ is an open-source Python toolkit for power system automation, providing a high-performance
wrapper for PowerWorld's Simulator Automation Server (SimAuto). It transforms complex COM calls
into intuitive, Pythonic operations.

- **Intuitive Indexing** — Access grid data with ``pw[Bus, "BusPUVolt"]`` syntax
- **Full SimAuto Coverage** — All PowerWorld API functions through modular mixins
- **Pandas Integration** — Every query returns a DataFrame
- **Pythonic Settings** — Solver and GIC options as descriptor attributes (``pw.max_iterations = 250``)
- **Convenience Methods** — Flows, overloads, PTDF/LODF, snapshot context manager, case summary
- **Transient Stability** — Fluent API with ``TS`` field intellisense
- **Analysis Utilities** — Built-in GIC, network topology, and contingency tools


Developed by **Luke Lowery** and **Adam Birchfield** at Texas A&M University
(`Birchfield Research Group <https://birchfield.engr.tamu.edu/>`_).
Licensed under `Apache 2.0 <https://www.apache.org/licenses/LICENSE-2.0>`_.

If you use ESA++ in research, please cite:

.. code-block:: bibtex

    @article{esa2020,
      title={Easy SimAuto (ESA): A Python Package for PowerWorld Simulator Automation},
      author={Mao, Zeyu and Thayer, Brandon and Liu, Yijing and Birchfield, Adam},
      year={2020}
    }

Installation
------------

Requires PowerWorld Simulator with SimAuto enabled and Python 3.9+.

.. code-block:: bash

    pip install esapp

Quick Example
-------------

.. code-block:: python

    from esapp import PowerWorld
    from esapp.components import *

    pw = PowerWorld("path/to/case.pwb")
    voltages = pw[Bus, "BusPUVolt"]      # read: DataFrame of key fields + BusPUVolt
    pw[Gen, Gen.GenMW] = 100.0           # write: fields as strings or typed members
    pw[Gen, Gen.GenStatus] = True        # bools serialize ("Closed"/"Open", "YES"/"NO")

See the :doc:`examples <examples/index>` for walkthroughs of reading data,
writing data, power flow, and workbench utilities.
