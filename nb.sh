#!/bin/bash

# Fire-prox notebook runner script
# This script runs Jupyter notebooks with Firebase emulators for testing
#
# Usage: ./nb.sh <notebook_path> [jupyter options]
#
# Examples:
#   ./nb.sh docs/phase1_demo_sync.ipynb                    # Run notebook with default options
#   ./nb.sh docs/phase1_demo_async.ipynb                   # Run async demo notebook
#   ./nb.sh docs/phase1_demo_sync.ipynb --ExecutePreprocessor.timeout=300
#
# The notebook will be executed in place, with outputs saved back to the notebook file.
# Execution stops on the first error encountered.

# Check if notebook path is provided
if [ $# -lt 1 ]; then
    echo "Error: No notebook path provided"
    echo ""
    echo "Usage: ./nb.sh <notebook_path> [jupyter options]"
    echo ""
    echo "Examples:"
    echo "  ./nb.sh docs/phase1_demo_sync.ipynb"
    echo "  ./nb.sh docs/phase1_demo_async.ipynb"
    exit 1
fi

NOTEBOOK_PATH="$1"
shift  # Remove first argument, keep any additional options

# Verify notebook exists
if [ ! -f "$NOTEBOOK_PATH" ]; then
    echo "Error: Notebook not found: $NOTEBOOK_PATH"
    exit 1
fi

# Build jupyter command
JUPYTER_CMD="uv run jupyter nbconvert --execute --to notebook --inplace"

# Add timeout (1 minute default)
JUPYTER_CMD="$JUPYTER_CMD --ExecutePreprocessor.timeout=60"

# Add the notebook path
JUPYTER_CMD="$JUPYTER_CMD $NOTEBOOK_PATH"

# If additional arguments are provided, append them
if [ $# -gt 0 ]; then
    JUPYTER_CMD="$JUPYTER_CMD $*"
fi

echo "Running notebook with Firebase emulators: $NOTEBOOK_PATH"
echo "Command: $JUPYTER_CMD"
echo ""

# Execute the command with Firebase emulators
pnpm exec firebase emulators:exec "$JUPYTER_CMD"

# Capture exit code
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Notebook executed successfully!"
    echo "  Outputs saved to: $NOTEBOOK_PATH"
else
    echo "✗ Notebook execution failed (exit code: $EXIT_CODE)"
    echo "  Check the notebook for error details: $NOTEBOOK_PATH"
fi

# Exit with the same code as the jupyter command
exit $EXIT_CODE
