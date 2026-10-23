#!/usr/bin/env python3
"""Start Beeline.  Run:  python3 beeline.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if "--fake-game" in sys.argv:
    from beeline.fakegame import main as fake_main
    fake_main()
else:
    try:
        from beeline.gui import main
    except ImportError as e:
        print("Beeline couldn't start because something is missing:", e)
        print("Run this, then try again:")
        print("  sudo apt install python3-tk python3-pil python3-pil.imagetk xdotool xserver-xephyr python3-xlib")
        sys.exit(1)
    main()
