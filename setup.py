import setuptools
import os
import re

with open("VERSION", "r") as fh:
    __version__ = fh.read()

with open("README.rst", "r") as fh:
    long_description = fh.read()

# Update the __version__ in __init__ before installing:
# Update the __version__ in __about__ before installing:
# Path to __init__.py:
init_path = os.path.join("gridwb", "__init__.py")
about_path = os.path.join("gridwb", "__about__.py")
# Read __init__.py:
with open(init_path, "r") as fh:
    __init__ = fh.read()

# Update the version:
__init__ = re.sub(
    r'__version__\s*=\s*[\'"][0-9]+\.[0-9]+\.[0-9]+[\'"]',
    '__version__ = "{}"'.format(__version__),
    __init__,
)

# Write new __init__.py:
with open(init_path, "w") as fh:
    fh.write(__init__)

# Read __about__.py:
with open(about_path, "r") as fh:
    __about__ = fh.read()

# Update the version:
__about__ = re.sub(
    r'__version__\s*=\s*[\'"][0-9]+\.[0-9]+\.[0-9]+[\'"]',
    '__version__ = "{}"'.format(__version__),
    __about__,
)

# Write new __about__.py:
with open(about_path, "w") as fh:
    fh.write(__about__)

setuptools.setup(
    name="gridwb",
    version=__version__,
    description="Grid Work Bench (GWB) is a platform-agnostic power-grid toolkit.",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    author="Adam Birchfield, Luke Lowery",
    author_email="abirchfield@tamu.edu, wyattluke.lowery@tamu.edu",
    url="GITLINKHERE",
    packages=setuptools.find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Microsoft :: Windows",
        "Development Status :: 5 - Production/Stable",
        "Environment :: Win32 (MS Windows)",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Topic :: Education",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development",
    ],
    keywords=[
        "Python",
        "PowerWorld",
        "PowerWorld Simulator",
        "Simulator",
        "PowerWorld Simulation Automation Server",
        "SimAuto",
        "Automation",
        "Power Systems",
        "Electric Power",
        "Power",
        "Easy SimAuto",
        "ESA",
        "Smart Grid",
        "Numpy",
        "Pandas",
    ],
    install_requires=[
        "pandas >= 0.25",
        "numpy >= 1.19.5",
        "scipy",
        "geopandas",
        "pywin32",
        "pypiwin32",       # TODO Double Check these to make sure we want them all
        "toolz",
        "networkx",
        "tqdm",
        "matplotlib",
        "pywt"
    ],
    python_requires=">=3.7",
    # There are a couple tests that use networkx, and we use the magic
    # of sphinx for documentation. Coverage is necessary to keep the
    # coverage report up to date.
    extras_require={
        "test": ["networkx", "coverage"],     
        "doc": ["sphinx", "tabulate", "sphinx_press_theme"], 
        "dev": ["pythran", "numba", "mypy", "black"],
    },
    license="Apache License 2.0",
    # TODO: Why aren't we zip safe?
    zip_safe=False,
)
