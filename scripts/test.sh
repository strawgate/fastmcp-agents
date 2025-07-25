#!/bin/bash

# Find all the pyproject.toml files in the project root (the parent of our current directory)
# Change directory to the directory of the pyproject.toml file
# Run uv run pytest -v tests/
# Change directory back to the original directory
set -e

pyproject_files=$(find .. -name "pyproject.toml" -not -path "*/.venv/*")

# Load environment variables from .env file
echo "Loading environment variables from .env file"
set -a; source ../.env; set +a

for pyproject_file in $pyproject_files; do
    # skip ../pyproject.toml
    if [ "$pyproject_file" == "../pyproject.toml" ]; then
        continue
    fi

    echo "Testing $pyproject_file"
    cd $(dirname $pyproject_file)
    uv run pytest -v tests/
    cd -
done