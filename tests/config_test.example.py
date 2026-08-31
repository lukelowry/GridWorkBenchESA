"""
Test configuration template for ESA++ tests.

Preferred: set the SAW_TEST_CASE environment variable (and optionally
SAW_GIC_TEST_CASES, a ';'-separated list of case paths) so machine-specific
paths never live in the repository. Environment variables take priority
over this file.

Alternative: copy this file to 'config_test.py' and update with your local
settings. The config_test.py file is gitignored.
"""

# Path to PowerWorld case file for integration tests
# Set to None to skip online tests
SAW_TEST_CASE = r"C:\Path\To\Your\Case.pwb"

# Optional: additional cases for the parametrized GIC tests
# GIC_TEST_CASES = [SAW_TEST_CASE, r"C:\Path\To\Another\Case.pwb"]
