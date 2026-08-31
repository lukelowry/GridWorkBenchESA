# ESA++ Test Suite

## Quick Start

```bash
pytest                         # Run all tests
pytest -k "not integration"    # Unit tests only (no PowerWorld)
pytest -m integration          # Integration tests only
```

**PowerWorld Setup**: Set the `SAW_TEST_CASE` environment variable to a case path
(and optionally `SAW_GIC_TEST_CASES`, a `;`-separated list for the parametrized
GIC tests). Alternatively, copy `config_test.example.py` to `config_test.py`.

## Test Categories

| Category | Description |
|----------|-------------|
| Unit | Mock-based tests, no PowerWorld required |
| Integration | Requires live PowerWorld connection |
| Component | Grid component and data access validation |

## Running with Coverage

```bash
pytest --cov=esapp --cov-report=html
```

## Configuration

Preferred: environment variables (keep machine-specific paths out of the repo):

```powershell
setx SAW_TEST_CASE "C:\path\to\test_case.pwb"
setx SAW_GIC_TEST_CASES "C:\path\case1.pwb;C:\path\case2.pwb"
```

Alternative: create `config_test.py` from the example template:

```python
SAW_TEST_CASE = r"C:\path\to\test_case.pwb"
```
