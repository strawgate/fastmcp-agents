#!/bin/bash

# Usage: list-projects.sh [--changed-only]
#   --changed-only: Only include projects that have changed since the last commit

CHANGED_ONLY=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --changed-only)
      CHANGED_ONLY=true
      shift
      ;;
    *)
      echo "Usage: $0 [--changed-only]"
      echo "  --changed-only: Only include projects that have changed since the last commit"
      exit 1
      ;;
  esac
done

# Find all projects with pyproject.toml
all_projects=$(find . -name "pyproject.toml" -not -path "*/.venv/*" -exec dirname {} \;)

# Build matrix data
matrix_data=""
changed_projects=""

while IFS= read -r project; do
  if [ -n "$project" ]; then
    # Skip the root project (namespace package only)
    if [ "$project" = "." ]; then
      continue
    fi
    
    # If --changed-only flag is set, check if project has changed
    if [ "$CHANGED_ONLY" = true ]; then
      if ! git diff --name-only HEAD~1 HEAD | grep -q "^${project#./}/"; then
        continue
      fi
    fi
    
    # Extract project name from pyproject.toml
    project_name=$(grep -h "^name = " "$project/pyproject.toml" | sed "s/name = //g" | sed "s/\"//g")
    
    if [ -z "$matrix_data" ]; then
      matrix_data="{\"pyproject\": \"$project\", \"project-name\": \"$project_name\"}"
      changed_projects="$project"
    else
      matrix_data="$matrix_data"$'\n'"{\"pyproject\": \"$project\", \"project-name\": \"$project_name\"}"
      changed_projects="$changed_projects"$'\n'"$project"
    fi
  fi
done <<< "$all_projects"

# Convert to JSON array
if [ -n "$matrix_data" ]; then
  matrix_json=$(echo "$matrix_data" | jq -s -c '.')
else
  matrix_json="[]"
fi

echo "matrix_json=$matrix_json"


# If --changed-only flag is set, also output the list of changed projects for debugging
if [ "$CHANGED_ONLY" = true ]; then
  echo "Changed projects:"
  echo "$changed_projects"
fi 

# if GITHUB_OUTPUT exists, echo the matrix to it
if [ -n "$GITHUB_OUTPUT" ]; then
  echo "matrix=$matrix_json" >> $GITHUB_OUTPUT
else
  echo "No GITHUB_OUTPUT environment variable found. Exiting."
fi