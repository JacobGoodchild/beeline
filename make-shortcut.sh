#!/bin/sh
# Adds Beeline to your Menu (under Games) and puts an icon on your Desktop.
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$HOME/.local/share/applications"
FILE="$HOME/.local/share/applications/beeline.desktop"
cat > "$FILE" <<EOT
[Desktop Entry]
Type=Application
Name=Beeline
Comment=Bee Swarm Simulator background macro
Exec=python3 "$DIR/beeline.py"
Path=$DIR
Icon=applications-games
Terminal=false
Categories=Game;
EOT
chmod +x "$FILE"
DESKTOP="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
if [ -d "$DESKTOP" ]; then
  cp "$FILE" "$DESKTOP/beeline.desktop"
  chmod +x "$DESKTOP/beeline.desktop"
  gio set "$DESKTOP/beeline.desktop" metadata::trusted true 2>/dev/null
fi
echo "Done. Beeline is now in your Menu under Games, and on your Desktop."
