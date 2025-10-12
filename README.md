# Fire-Prox

[![CI](https://github.com/habemus-papadum/fire-prox/actions/workflows/ci.yml/badge.svg)](https://github.com/habemus-papadum/fire-prox/actions/workflows/ci.yml)
[![Coverage](https://raw.githubusercontent.com/habemus-papadum/fire-prox/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/habemus-papadum/fire-prox/blob/python-coverage-comment-action-data/htmlcov/index.html)
[![Documentation](https://img.shields.io/badge/Documentation-blue.svg)](https://habemus-papadum.github.io/fire-prox/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

## Setup

Before running tests or using the project, make sure to install all dependencies:

```bash
# Install Python dependencies
uv sync --frozen

# Install Node.js dependencies (for Firebase tools)
pnpm install
```

## Testing

The project includes a flexible test runner that makes it easy to pass additional parameters to pytest while running Firebase emulators. The test runner launches a local Firestore emulator that Python code is configured to interact with by default and then tears down the emulator once the unit tests are done.

### VSCode & Demo Notebooks
For running test in vscode or using the demo notebooks, you need to launch the developer emulator using `pnpm developer-emulator`. 

### Running Tests

You can run tests in several ways:

```bash
# Using the bash script directly
./test.sh

# Using npm/pnpm (calls the bash script)
pnpm test

# With additional pytest parameters
./test.sh -v                     # Verbose output
./test.sh -k test_specific       # Run specific test
./test.sh --tb=short            # Short traceback format
./test.sh -v -k test_fire_prox  # Combine multiple options
```

The test script automatically starts Firebase emulators and runs your tests within that environment, then cleans up afterward.

### Firestore Test Harness

Tests can rely on the `firestore_test_harness` pytest fixture (published in `fire_prox.testing`) to ensure the emulator database is fully deleted both before a test starts and after it finishes. The harness can also be used as a context manager when writing ad-hoc scripts:

```python
from google.cloud import firestore
from fire_prox.testing import firestore_harness

with firestore_harness() as harness:
    client = firestore.Client(project=harness.project_id)
    # interact with Firestore here
```


