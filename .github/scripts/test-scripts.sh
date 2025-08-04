#!/bin/bash

echo "Testing list-projects.sh (all projects):"
echo "========================================"
.github/scripts/list-projects.sh
echo ""
echo "Testing list-projects.sh (changed projects only):"
echo "================================================"
.github/scripts/list-projects.sh --changed-only 