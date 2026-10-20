#!/usr/bin/env bash
# Copy the built datapack and guest scripts into the VM, then reload the datapack.
set -euo pipefail
cd "$(dirname "$0")"
OUT=../../experiments/minecraft-pve-standard-2026-10-19
TMP=$(mktemp -d)
COPYFILE_DISABLE=1 tar --no-xattrs --no-mac-metadata -C "$OUT" -czf "$TMP/pack.tgz" datapack
limactl copy "$TMP/pack.tgz" minecraft-lab:/tmp/pack.tgz
limactl shell minecraft-lab mkdir -p minecraft-lab/pve-standard-tools
for f in guest_trial.py core.py command.py; do limactl copy "$f" "minecraft-lab:minecraft-lab/pve-standard-tools/$f"; done
limactl shell minecraft-lab bash -c 'set -e; W="$HOME/.local/share/PrismLauncher/instances/26.3/minecraft/saves/Astra Natural PVE"; rm -rf "$W/datapacks/pve" /tmp/pk; mkdir /tmp/pk; tar -C /tmp/pk -xzf /tmp/pack.tgz; mv /tmp/pk/datapack "$W/datapacks/pve"'
limactl shell minecraft-lab python3 minecraft-lab/pve-standard-tools/command.py reload
rm -rf "$TMP"
