#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
  xvfb openbox xdotool x11-utils x11-xserver-utils xauth x11vnc novnc websockify \
  mesa-utils libgl1-mesa-dri libglx-mesa0 libegl1 libopenal1 libfuse2t64 \
  libxkbcommon-x11-0 libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
  libxcb-render-util0 libxcb-xinerama0 libnss3 libasound2t64 libpulse0 \
  dbus-x11 xterm curl ca-certificates unzip python3-pip python3-venv \
  python3-pil python3-xlib scrot ffmpeg openjdk-21-jre openjdk-25-jre wmctrl \
  mesa-vulkan-drivers vulkan-tools
mkdir -p "$HOME/minecraft-lab" "$HOME/.vnc" "$HOME/.config/systemd/user" "$HOME/.local/bin"
chmod 700 "$HOME/.vnc"
if [ ! -s "$HOME/.vnc/password.txt" ]; then
  python3 -c 'import secrets; print(secrets.token_urlsafe(18))' > "$HOME/.vnc/password.txt"
  chmod 600 "$HOME/.vnc/password.txt"
  x11vnc -storepasswd "$(cat "$HOME/.vnc/password.txt")" "$HOME/.vnc/passwd" >/dev/null
fi
cat > "$HOME/.config/systemd/user/minecraft-display.service" <<'UNIT'
[Unit]
Description=Isolated Minecraft virtual desktop
[Service]
ExecStart=/usr/bin/Xvfb :99 -screen 0 1280x720x24 -nolisten tcp -noreset
Restart=on-failure
[Install]
WantedBy=default.target
UNIT
cat > "$HOME/.config/systemd/user/minecraft-desktop.service" <<'UNIT'
[Unit]
Description=Minecraft window manager
After=minecraft-display.service
Requires=minecraft-display.service
[Service]
Environment=DISPLAY=:99
ExecStart=/usr/bin/dbus-run-session /usr/bin/openbox-session
Restart=on-failure
[Install]
WantedBy=default.target
UNIT
cat > "$HOME/.config/systemd/user/minecraft-vnc.service" <<'UNIT'
[Unit]
Description=Loopback-only Minecraft desktop viewer
After=minecraft-display.service
Requires=minecraft-display.service
[Service]
Environment=DISPLAY=:99
ExecStart=/usr/bin/x11vnc -display :99 -localhost -rfbport 5900 -rfbauth %h/.vnc/passwd -forever -shared -noxdamage -quiet
Restart=on-failure
[Install]
WantedBy=default.target
UNIT
cat > "$HOME/.config/systemd/user/minecraft-web.service" <<'UNIT'
[Unit]
Description=Loopback-only browser desktop viewer
After=minecraft-vnc.service
Requires=minecraft-vnc.service
[Service]
ExecStart=/usr/bin/websockify --web=/usr/share/novnc 127.0.0.1:6080 127.0.0.1:5900
Restart=on-failure
[Install]
WantedBy=default.target
UNIT
sudo loginctl enable-linger "$USER"
systemctl --user daemon-reload
systemctl --user enable --now minecraft-display minecraft-desktop minecraft-vnc minecraft-web
curl -fL --retry 3 https://github.com/PrismLauncher/PrismLauncher/releases/download/11.1.1/PrismLauncher-Linux-aarch64.AppImage -o "$HOME/minecraft-lab/PrismLauncher.AppImage"
chmod +x "$HOME/minecraft-lab/PrismLauncher.AppImage"
cd "$HOME/minecraft-lab"
./PrismLauncher.AppImage --appimage-extract >/dev/null
cat > "$HOME/.local/bin/minecraft-launcher" <<'LAUNCH'
#!/usr/bin/env bash
export DISPLAY=:99
export LIBGL_ALWAYS_SOFTWARE=1
exec "$HOME/minecraft-lab/squashfs-root/AppRun" "$@"
LAUNCH
chmod +x "$HOME/.local/bin/minecraft-launcher"
cat > "$HOME/.config/systemd/user/minecraft-launcher.service" <<'UNIT'
[Unit]
Description=Prism Launcher in the isolated VM
After=minecraft-desktop.service
Requires=minecraft-desktop.service
[Service]
Environment=DISPLAY=:99
Environment=LIBGL_ALWAYS_SOFTWARE=1
Environment=LP_NUM_THREADS=6
ExecStart=%h/.local/bin/minecraft-launcher
[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
DISPLAY=:99 glxinfo -B
