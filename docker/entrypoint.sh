#!/bin/sh
# Starts the virtual screen and noVNC, keeps all app state in /data, then runs the command.
set -e

DATA=/data
mkdir -p "$DATA/downloads" "$DATA/saved_sessions" "$DATA/logs" "$DATA/browser-profile"

# Everything the app writes lives in the /data volume, so it survives rebuilds and restarts.
# Dangling links are fine: the app treats a missing file as "not saved yet".
for dir in downloads saved_sessions logs; do
  ln -sfn "$DATA/$dir" "/app/$dir"
done
ln -sfn "$DATA/browser-profile" "/app/.ashzo_browser"
# No browser is running yet, so any lock in the profile is left over from the last container.
# Chrome refuses to start on a lock that names another computer (a recreated container has a new hostname).
rm -f "$DATA/browser-profile"/SingletonLock "$DATA/browser-profile"/SingletonCookie "$DATA/browser-profile"/SingletonSocket
for file in ashzo_settings.json sessions.json session_cookies.json flow_auth_state.json learned_routes.json; do
  ln -sfn "$DATA/$file" "/app/$file"
done

# Virtual screen for the Ashzo Browser (DISPLAY=:99).
Xvfb :99 -screen 0 1440x900x24 -nolisten tcp >"$DATA/logs/xvfb.log" 2>&1 &
for _ in $(seq 1 20); do
  [ -e /tmp/.X11-unix/X99 ] && break
  sleep 0.5
done

# noVNC: view the Ashzo Browser at http://localhost:6080/vnc.html (sign in to Google there).
if [ -n "$VNC_PASSWORD" ]; then
  x11vnc -storepasswd "$VNC_PASSWORD" /tmp/vncpass >/dev/null 2>&1
  VNC_AUTH="-rfbauth /tmp/vncpass"
else
  VNC_AUTH="-nopw"
fi
x11vnc -display :99 -forever -shared -quiet -rfbport 5900 $VNC_AUTH >"$DATA/logs/x11vnc.log" 2>&1 &
websockify --web /usr/share/novnc 6080 localhost:5900 >"$DATA/logs/novnc.log" 2>&1 &

exec "$@"
