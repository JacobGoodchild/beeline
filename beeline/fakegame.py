"""A stand-in game window for dry runs without Roblox.

Run it inside the hidden screen:   DISPLAY=:5 python3 beeline.py --fake-game
It draws a fake bag meter that fills while you hold the left mouse in the "field",
a fake hive with an E-prompt and a balloon that empties after E is pressed, and a
fake Saturator.  The real macro can then be pointed at it.

Options:  --fast        fill / convert quicker (for automatic tests)
          --state FILE  write the fake game's counters to FILE as JSON every second
"""

from __future__ import annotations

import json
import sys
import time
import tkinter as tk

from PIL import ImageTk

from .fakeworld import FakeWorld


class FakeGame:
    def __init__(self, fast: bool = False, state_file: str | None = None) -> None:
        self.world = FakeWorld()
        if fast:
            self.world.fill_rate = 10.0
            self.world.convert_rate = 20.0
            self.world.balloon_rate = 4.0
        self.state_file = state_file
        self.root = tk.Tk()
        self.root.title("Beeline fake game")
        self.root.geometry("1280x720+0+0")
        self.canvas = tk.Canvas(self.root, width=1280, height=720, highlightthickness=0)
        self.canvas.pack()
        self.root.bind("<KeyPress>", lambda e: self.world.key("keydown", e.keysym))
        self.root.bind("<KeyRelease>", lambda e: self.world.key("keyup", e.keysym))
        self.canvas.bind("<ButtonPress-1>", lambda e: self.world.mouse("down"))
        self.canvas.bind("<ButtonRelease-1>", lambda e: self.world.mouse("up"))
        self.last = time.monotonic()
        self.last_state = 0.0
        self.root.after(50, self.frame)

    def frame(self) -> None:
        now = time.monotonic()
        self.world.advance(now - self.last)
        self.last = now
        self._photo = ImageTk.PhotoImage(self.world.screenshot())
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        if self.state_file and now - self.last_state > 1.0:
            self.last_state = now
            self.write_state()
        self.root.after(80, self.frame)

    def write_state(self) -> None:
        w = self.world
        data = {"x": w.x, "y": w.y, "bag": w.bag, "balloon": w.balloon, "converting": w.converting,
                "sprinkler_presses": w.sprinkler_presses, "e_presses": w.e_presses,
                "left_mid_convert": w.left_mid_convert, "blocked_seen": w.blocked_seen,
                "saturator": w.saturator, "max_gap": w.max_gap, "held": sorted(w.held),
                "mouse_held": w.mouse_held, "keys": [n for (_, n) in w.keys_log]}
        with open(self.state_file + ".tmp", "w") as f:
            json.dump(data, f)
        import os
        os.replace(self.state_file + ".tmp", self.state_file)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    args = sys.argv[1:]
    state = None
    if "--state" in args:
        state = args[args.index("--state") + 1]
    FakeGame(fast="--fast" in args, state_file=state).run()


if __name__ == "__main__":
    main()
