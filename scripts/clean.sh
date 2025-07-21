## Remove all .venv directories, .pyi files and __pycache__ directories

find .. -name "*.venv" -type d -exec rm -rf {} \;
find .. -name "*.pyi" -type f -exec rm -f {} \;
find .. -name "__pycache__" -type d -exec rm -rf {} \;
find .. -name ".ruff_cache" -type d -exec rm -rf {} \;
find .. -name ".pytest_cache" -type d -exec rm -rf {} \;
find .. -name "dist" -type d -exec rm -rf {} \;