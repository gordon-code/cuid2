#!/usr/bin/env bash

# Ensure script fails fast
set -euo pipefail

## Set default variables
# Current directory - https://stackoverflow.com/a/246128
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
# Verify PDM is installed
set +e
PDM_BIN=$(which pdm)
if [ $? -ne 0 ]; then
    echo "PDM is not installed. Please install PDM before running this script."
    echo "https://pdm.fming.dev/dev/#installation"
    exit 1
fi
set -e

# Handle call with wrong command
function wrong_command() {
    echo "${0##*/} - unknown command: '${1}'" >&2
    usage_message
    exit 1
}

# Print help / script usage
function usage_message() {
    cat <<-EOF
		Usage: $SCRIPT_DIR/${0##*/} <command>
		Available commands are:
		    all         Check all project dependencies
		    outdated    Check only outdated project dependencies
		    <group>     Check dependencies for a specific group
EOF
}

set_variables() {
    local package=$1
    pkg_name=$(echo $package | sed -r "s/([^~=!<>]+)[~=!<>]*.*/\1/")
    pdm_show_output=$($PDM_BIN show $pkg_name)
    current_version=$(echo "$pdm_show_output" | grep "Installed version" | cut -w -f3)
    latest_version=$(echo "$pdm_show_output" | grep "Latest stable version" | cut -w -f4)
    set +e
    # Use of `xargs` is to remove any trailing whitespace (https://linuxhint.com/trim_string_bash/)
    homepage_url=$(echo "$pdm_show_output" | grep -v "sponsors" | grep -oEm 1 "https?:\/\/git(hub|lab)\.com\/[^\/]+\/[^\/]+\/?\s*\$" | xargs)
    # It's possible for a package to not have a homepage URL, so we can attempt to just catch any URL
    if [ -z "$homepage_url" ]; then
        homepage_url=$(echo "$pdm_show_output" | grep -v "sponsors" | grep -oEm 1 "https?:\/\/[^\/]+\/[^\/]+\/?\s*\$" | xargs)
    fi
    # And if that fails, we can just leave it blank
    if [ -z "$homepage_url" ]; then
        homepage_url=""
    fi
    set -e
}

function check_all_dependencies() {
    echo "Checking all dependencies..."
    echo

    echo "dependencies = ["

    for PKG in $($PDM_BIN export --without-hashes --pyproject --production | grep -v "^#"); do
        if test -n "$PKG"; then
            set_variables $PKG
            echo -e "\t\"$PKG\", # $homepage_url (latest: $latest_version)"
        fi
    done | column -t

    echo "]"
    echo

    echo "[tool.pdm.dev-dependencies]"

    for DEV_GROUP in $($PDM_BIN list --fields groups --json | jq -r '.[] | select(.groups != ":sub" and .groups != "default") | .groups' | sort | uniq); do
        echo "$DEV_GROUP = ["

        for PKG in $($PDM_BIN export --without-hashes --pyproject --no-default -G $DEV_GROUP | grep -v "^#"); do
            if test -n "$PKG"; then
                set_variables $PKG
                echo -e "\t\"$PKG\", # $homepage_url (latest: $latest_version)"
            fi
        done | column -t

        echo "]"
    done
}

function check_group_dependencies() {
    local group_name="$1"
    local group_list="$($PDM_BIN list --fields groups --json | jq -r '.[] | select(.groups != ":sub" and .groups != "default") | .groups' | sort | uniq)"

    if [[ $group_list != *"$group_name"* ]]; then
        wrong_command "$group_name"
    fi

    echo "Checking $group_name dependencies..."
    echo

    echo "$group_name = ["

    for PKG in $($PDM_BIN export --without-hashes --pyproject --no-default -G $group_name | grep -v "^#"); do
        if test -n "$PKG"; then
            set_variables $PKG
            echo -e "\t\"$PKG\", # $homepage_url (latest: $latest_version)"
        fi
    done | column -t

    echo "]"
}

function check_outdated_dependencies() {
    echo "Checking only outdated dependencies..."
    echo

    for PKG in $($PDM_BIN export --without-hashes --pyproject | grep -v "^#"); do
        if test -n "$PKG"; then
            set_variables $PKG
            if [ "$current_version" != "$latest_version" ]; then
                echo -e "\t\"$PKG\", # ${homepage_url%%*( )} (latest: $latest_version)"
            fi
        fi
    done | column -t
}

# Handle command argument
case "${1-}" in
    all) check_all_dependencies;;
    outdated) check_outdated_dependencies;;
    *) check_group_dependencies "$1";;
esac
