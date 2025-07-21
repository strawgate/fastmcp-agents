#!/bin/bash

# Find all the pyproject.toml files in the project root (the parent of our current directory)
# Change directory to the directory of the pyproject.toml file
# Run uv build and pytest
# Change directory back to the original directory
set -e

pyproject_files=$(find .. -name "pyproject.toml" -not -path "*/.venv/*")

for pyproject_file in $pyproject_files; do
    echo "Building and testing $pyproject_file"
    cd $(dirname $pyproject_file)
    uv venv
    source .venv/bin/activate
    uv build
    # if there is a tests/ directory, run pytest
    if [ -d "tests/" ]; then
        uv run pytest -v tests/
    fi
    deactivate
    cd -
done