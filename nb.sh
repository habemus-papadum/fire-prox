#!/bin/bash

# Fire-prox notebook runner script
# This script runs Jupyter notebooks with Firebase emulators for testing
#
# Usage: ./nb.sh [--check-outputs] [--no-inplace] <notebook_path> [jupyter options]
#
# Options:
#   --check-outputs    Compare outputs before and after execution to detect changes
#   --no-inplace       Execute notebook without modifying the original file
#
# Examples:
#   ./nb.sh docs/phase1_demo_sync.ipynb                    # Run notebook with default options
#   ./nb.sh --check-outputs docs/phase1_demo_async.ipynb   # Run and check if outputs changed
#   ./nb.sh --no-inplace docs/phase1_demo_sync.ipynb       # Run without modifying the file
#   ./nb.sh docs/phase1_demo_sync.ipynb --ExecutePreprocessor.timeout=300
#
# By default, the notebook will be executed in place, with outputs saved back to the notebook file.
# Use --no-inplace to prevent modifications (useful in CI environments).
# Execution stops on the first error encountered.

# Parse flags
CHECK_OUTPUTS=false
NO_INPLACE=false
while [[ "$1" == --* ]]; do
    case "$1" in
        --check-outputs)
            CHECK_OUTPUTS=true
            shift
            ;;
        --no-inplace)
            NO_INPLACE=true
            shift
            ;;
        *)
            break
            ;;
    esac
done

# Check if notebook path is provided
if [ $# -lt 1 ]; then
    echo "Error: No notebook path provided"
    echo ""
    echo "Usage: ./nb.sh [--check-outputs] [--no-inplace] <notebook_path> [jupyter options]"
    echo ""
    echo "Options:"
    echo "  --check-outputs    Compare outputs before and after execution"
    echo "  --no-inplace       Execute without modifying the original file"
    echo ""
    echo "Examples:"
    echo "  ./nb.sh docs/phase1_demo_sync.ipynb"
    echo "  ./nb.sh --check-outputs docs/phase1_demo_async.ipynb"
    echo "  ./nb.sh --no-inplace docs/phase1_demo_sync.ipynb"
    exit 1
fi

NOTEBOOK_PATH="$1"
shift  # Remove first argument, keep any additional options

# Verify notebook exists
if [ ! -f "$NOTEBOOK_PATH" ]; then
    echo "Error: Notebook not found: $NOTEBOOK_PATH"
    exit 1
fi

# Function to extract outputs from notebook (ignoring metadata)
extract_outputs() {
    local notebook="$1"
    # Extract outputs from each cell, removing execution_count and other metadata
    # We keep: output_type, text, data, name (for stream outputs)
    # Skip cells tagged with 'nondet' (non-deterministic)
    python3 -c "
import json
import sys

with open('$notebook', 'r') as f:
    nb = json.load(f)

outputs = []
for cell in nb.get('cells', []):
    # Skip cells tagged with 'nondet' (non-deterministic outputs)
    tags = cell.get('metadata', {}).get('tags', [])
    if 'nondet' in tags:
        outputs.append([])  # Add empty list to maintain cell indexing
        continue

    cell_outputs = []
    for output in cell.get('outputs', []):
        # Create a cleaned output dict with just the content
        cleaned = {
            'output_type': output.get('output_type')
        }
        # Add relevant fields based on output type
        if 'text' in output:
            cleaned['text'] = output['text']
        if 'data' in output:
            cleaned['data'] = output['data']
        if 'name' in output:
            cleaned['name'] = output['name']
        if 'ename' in output:
            cleaned['ename'] = output['ename']
        if 'evalue' in output:
            cleaned['evalue'] = output['evalue']
        if 'traceback' in output:
            cleaned['traceback'] = output['traceback']
        cell_outputs.append(cleaned)
    outputs.append(cell_outputs)

json.dump(outputs, sys.stdout, indent=2, sort_keys=True)
" 2>/dev/null
}

# Save outputs before execution if checking
TEMP_BEFORE=""
if [ "$CHECK_OUTPUTS" = true ]; then
    TEMP_BEFORE=$(mktemp)
    echo "Extracting outputs before execution..."
    extract_outputs "$NOTEBOOK_PATH" > "$TEMP_BEFORE"
fi

# Build jupyter command
TEMP_OUTPUT=""
TEMP_DIR=""
if [ "$NO_INPLACE" = true ]; then
    # Create temp directory and file for output
    TEMP_DIR=$(mktemp -d)
    TEMP_OUTPUT="$TEMP_DIR/output.ipynb"
    JUPYTER_CMD="uv run jupyter nbconvert --execute --to notebook --output-dir=$TEMP_DIR --output=output"
else
    JUPYTER_CMD="uv run jupyter nbconvert --execute --to notebook --inplace"
fi

# Add timeout (1 minute default)
JUPYTER_CMD="$JUPYTER_CMD --ExecutePreprocessor.timeout=60"

# Add the notebook path
JUPYTER_CMD="$JUPYTER_CMD $NOTEBOOK_PATH"

# If additional arguments are provided, append them
if [ $# -gt 0 ]; then
    JUPYTER_CMD="$JUPYTER_CMD $*"
fi

echo "Running notebook with Firebase emulators: $NOTEBOOK_PATH"
if [ "$NO_INPLACE" = true ]; then
    echo "Mode: Execute only (no file modification)"
else
    echo "Mode: Execute and save outputs in-place"
fi
echo "Command: $JUPYTER_CMD"
echo ""

# Set NOTEBOOK_CI to indicate running in CI/test environment
export NOTEBOOK_CI=1

# Execute the command with Firebase emulators
pnpm exec firebase emulators:exec "$JUPYTER_CMD"

# Capture exit code
EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Notebook executed successfully!"
    if [ "$NO_INPLACE" = true ]; then
        echo "  Original file unchanged: $NOTEBOOK_PATH"
    else
        echo "  Outputs saved to: $NOTEBOOK_PATH"
    fi

    # Check if outputs changed (if requested)
    if [ "$CHECK_OUTPUTS" = true ]; then
        echo ""
        echo "Comparing outputs..."
        TEMP_AFTER=$(mktemp)

        # Extract outputs from the executed notebook
        if [ "$NO_INPLACE" = true ]; then
            # Use temp output file if no-inplace mode
            extract_outputs "$TEMP_OUTPUT" > "$TEMP_AFTER"
        else
            # Use original notebook file if inplace mode
            extract_outputs "$NOTEBOOK_PATH" > "$TEMP_AFTER"
        fi

        if diff -q "$TEMP_BEFORE" "$TEMP_AFTER" > /dev/null 2>&1; then
            echo "✓ Outputs unchanged - notebook is stable"
            rm -f "$TEMP_BEFORE" "$TEMP_AFTER"
        else
            echo "⚠ Outputs changed during execution"
            echo ""
            echo "Differences detected (excluding metadata like execution_count):"
            echo "================================================================"
            diff -u "$TEMP_BEFORE" "$TEMP_AFTER" || true
            echo "================================================================"
            echo ""
            echo "This may indicate:"
            echo "  - Notebook outputs were stale/outdated"
            echo "  - Non-deterministic behavior in notebook code"
            echo "  - Changes in dependencies or environment"
            rm -f "$TEMP_BEFORE" "$TEMP_AFTER"

            # Clean up temp output if exists
            if [ -n "$TEMP_DIR" ]; then
                rm -rf "$TEMP_DIR"
            fi

            exit 2  # Exit with code 2 to indicate outputs changed
        fi
    fi

    # Clean up temp output directory if it exists
    if [ -n "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
else
    echo "✗ Notebook execution failed (exit code: $EXIT_CODE)"
    echo "  Check the notebook for error details: $NOTEBOOK_PATH"

    # Clean up temp files if they exist
    if [ -n "$TEMP_BEFORE" ]; then
        rm -f "$TEMP_BEFORE"
    fi
    if [ -n "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
fi

# Exit with the same code as the jupyter command
exit $EXIT_CODE
