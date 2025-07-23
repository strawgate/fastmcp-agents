#!/bin/bash

# Find all the pyproject.toml files in the project root (the parent of our current directory)
# Change directory to the directory of the pyproject.toml file
# Run uv sync
# Change directory back to the original directory


pyproject_files=$(find .. -name "pyproject.toml" -not -path "*/.venv/*")

for pyproject_file in $pyproject_files; do
    echo "Syncing $pyproject_file"
    cd $(dirname $pyproject_file)
    uv sync --all-projects
    cd -
done