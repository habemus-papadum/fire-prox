#!/bin/bash

# test_notebooks.sh - Run all demo notebooks from mkdocs.yml
#
# This script extracts notebook paths from mkdocs.yml and runs each one
# through nb.sh to verify they execute without errors.
#
# Usage: ./test_notebooks.sh [--check-outputs] [--no-inplace]
#
# Options:
#   --check-outputs    Verify that notebook outputs don't change during execution
#   --no-inplace       Execute notebooks without modifying the original files

set -e

# Parse flags
NB_FLAGS=""
while [[ "$1" == --* ]]; do
    case "$1" in
        --check-outputs)
            NB_FLAGS="$NB_FLAGS --check-outputs"
            shift
            ;;
        --no-inplace)
            NB_FLAGS="$NB_FLAGS --no-inplace"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MKDOCS_FILE="$SCRIPT_DIR/mkdocs.yml"
DOCS_DIR="docs"

# Check if mkdocs.yml exists
if [ ! -f "$MKDOCS_FILE" ]; then
    echo "Error: mkdocs.yml not found at $MKDOCS_FILE"
    exit 1
fi

# Check if nb.sh exists and is executable
if [ ! -x "$SCRIPT_DIR/nb.sh" ]; then
    echo "Error: nb.sh not found or not executable at $SCRIPT_DIR/nb.sh"
    exit 1
fi

echo "==================================================================="
echo "Testing Demo Notebooks from mkdocs.yml"
if [ -n "$NB_FLAGS" ]; then
    echo "Flags:$NB_FLAGS"
else
    echo "Mode: Execute and save in-place"
    echo "(Use --no-inplace to prevent file modification in CI)"
fi
echo "==================================================================="
echo ""

# Extract notebook paths from mkdocs.yml
# Look for lines that end with .ipynb in the nav section
NOTEBOOKS=$(grep -E '\.ipynb$' "$MKDOCS_FILE" | sed 's/.*: //' | sed 's/ //g')

if [ -z "$NOTEBOOKS" ]; then
    echo "No notebooks found in mkdocs.yml"
    exit 0
fi

# Track results
TOTAL=0
PASSED=0
FAILED=0
FAILED_NOTEBOOKS=""

# Run each notebook
while IFS= read -r notebook_path; do
    # Skip empty lines
    if [ -z "$notebook_path" ]; then
        continue
    fi

    TOTAL=$((TOTAL + 1))

    # Prepend docs/ to the path since mkdocs.yml paths are relative to docs_dir
    FULL_PATH="$DOCS_DIR/$notebook_path"

    echo "-------------------------------------------------------------------"
    echo "[$TOTAL] Running: $FULL_PATH"
    echo "-------------------------------------------------------------------"

    # Run the notebook through nb.sh
    if "$SCRIPT_DIR/nb.sh" $NB_FLAGS "$FULL_PATH"; then
        echo "✓ PASSED: $notebook_path"
        PASSED=$((PASSED + 1))
    else
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 2 ]; then
            echo "⚠ OUTPUTS CHANGED: $notebook_path"
        else
            echo "✗ FAILED: $notebook_path"
        fi
        FAILED=$((FAILED + 1))
        FAILED_NOTEBOOKS="$FAILED_NOTEBOOKS  - $notebook_path (exit code: $EXIT_CODE)\n"
    fi

    echo ""
done <<< "$NOTEBOOKS"

# Print summary
echo "==================================================================="
echo "Test Summary"
echo "==================================================================="
echo "Total notebooks: $TOTAL"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo ""

if [ $FAILED -gt 0 ]; then
    echo "Failed notebooks:"
    echo -e "$FAILED_NOTEBOOKS"
    exit 1
else
    echo "✓ All notebooks passed!"
    exit 0
fi
