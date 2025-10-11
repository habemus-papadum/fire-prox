# Fire-Prox

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

