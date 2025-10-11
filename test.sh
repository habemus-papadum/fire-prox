#!/bin/bash

# Fire-prox test runner script
# This script allows passing additional parameters to pytest while running Firebase emulators
# 
# Usage: ./test.sh [pytest options]
# 
# Examples:
#   ./test.sh                           # Run all tests with default options
#   ./test.sh -v                        # Run with verbose output
#   ./test.sh -k test_specific          # Run specific test matching pattern
#   ./test.sh --tb=short                # Use short traceback format
#   ./test.sh -v -k test_fire_prox      # Combine multiple options
#   ./test.sh -x --tb=short             # Stop on first failure with short traceback
#   ./test.sh --cov=src                 # Run with coverage for src directory
#
# For all pytest options, run: ./test.sh --help

# Default pytest command with basic options
PYTEST_CMD="uv run pytest -s"

# If additional arguments are provided, append them to the pytest command
if [ $# -gt 0 ]; then
    PYTEST_CMD="$PYTEST_CMD $*"
fi

echo "Running Firebase emulators with: $PYTEST_CMD"

# Execute the command with Firebase emulators
pnpm exec firebase emulators:exec "$PYTEST_CMD"

# Exit with the same code as the pytest command
exit $?