#!/usr/bin/env sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
export MSYS2_ARG_CONV_EXCL="*"

docker run --rm -v "${SCRIPT_DIR}:/workspace" structurizr/cli "$@"
