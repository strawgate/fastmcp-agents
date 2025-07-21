

## This script takes an argument of a version number and then
# finds all the pyproject.toml files and updates the version number
# in the [project] section.
# It then commits the changes and pushes them to the remote repository.

# Get the version number from the command line
version=$1

# Find all the pyproject.toml files and update the version number

projectfiles=$(find .. -name "pyproject.toml")

for file in $projectfiles; do
    sed -i.bak "s/^version = .*$/version = \"$version\"/" $file
done

./sync.sh
