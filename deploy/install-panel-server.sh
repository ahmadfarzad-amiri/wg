#!/usr/bin/env bash
# Deprecated: use install-entry-server.sh (entry server + panels).
exec bash "$(dirname "${BASH_SOURCE[0]}")/install-entry-server.sh" "$@"
