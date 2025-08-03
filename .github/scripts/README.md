# GitHub Scripts

This directory contains bash scripts used by GitHub Actions workflows.

## Scripts

### `list-projects.sh`
Lists projects with `pyproject.toml` files and extracts their project names.

**Options:**
- `--changed-only`: Only include projects that have changed since the last commit

**Output:** `matrix=<json_array>` where each object contains `pyproject` (directory path) and `project-name` (from pyproject.toml).

**Usage:**
```bash
# List all projects
.github/scripts/list-projects.sh

# List only changed projects
.github/scripts/list-projects.sh --changed-only
```

### `test-scripts.sh`
Tests the script in both modes to ensure it works correctly.

**Usage:**
```bash
.github/scripts/test-scripts.sh
```

## Testing Locally

You can test the script locally to verify it works as expected:

```bash
# Test both modes
.github/scripts/test-scripts.sh

# Test individual modes
.github/scripts/list-projects.sh
.github/scripts/list-projects.sh --changed-only
```

## Matrix Format

Both scripts output a matrix format compatible with GitHub Actions:

```json
[
  {
    "pyproject": "./fastmcp-agents-cli",
    "project-name": "fastmcp-agents-cli"
  },
  {
    "pyproject": "./fastmcp-agents-bridge/fastmcp_agents_bridge_pydantic_ai",
    "project-name": "fastmcp-agents-bridge-pydantic-ai"
  }
]
```

This format ensures that each job runs with the correct project path and name paired together, avoiding Cartesian product issues. 