#!/usr/bin/env bash
# Build and start the mcbench env server on 127.0.0.1:8765.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
cache="${MCBENCH_CACHE:-$HOME/.cache/mcbench/minestudio}"
mkdir -p "$cache"
docker build -t mcbench-env "$here"
docker rm -f mcbench-env >/dev/null 2>&1 || true
# No --platform flag: with the containerd image store it fails to find the local image.
docker run -d --name mcbench-env --cpus "${MCBENCH_CPUS:-2}" -p 127.0.0.1:8765:8765 -v "$cache:/msdir" mcbench-env
echo "mcbench-env started; check with: curl -s http://127.0.0.1:8765/health"
