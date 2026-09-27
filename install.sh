#!/usr/bin/env bash
set -euo pipefail

# Install the Python entry point as /usr/local/bin/epilint.
# Set PREFIX to install elsewhere, for example: PREFIX="$HOME/.local" bash install.sh
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source_file="$script_dir/epilint.py"
prefix=${PREFIX:-/usr/local}
target_dir="$prefix/bin"

if [[ ! -f "$source_file" ]]; then
    printf 'Error: %s is missing. Run this script from a complete epilint checkout.\n' "$source_file" >&2
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))'; then
    printf 'Error: epilint requires Python 3.9 or newer.\n' >&2
    exit 1
fi

if ! install -d -m 755 -- "$target_dir" || ! install -m 755 -- "$source_file" "$target_dir/epilint"; then
    printf 'Error: installation failed. For /usr/local/bin, run: sudo bash install.sh\n' >&2
    exit 1
fi

printf 'Installed epilint to %s\n' "$target_dir/epilint"
