#!/usr/bin/env bash
set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "$(dirname "$0")"
./mcvm start
./mcvm launcher
printf '\nLocal desktop password (keep private):\n'
./mcvm password
open 'http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale'
