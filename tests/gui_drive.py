"""Drives the real Beeline GUI like Jacob would, against the fake game.

Run by tests/test_gui_e2e.py inside a virtual desktop.  Needs DISPLAY (the pretend
desktop), BEELINE_DATA (a temp folder) and argv[1] = folder for screenshots.
Exits 0 on success and prints what happened.
"""

import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from tkinter import messagebox  # noqa: E402

from PIL import ImageGrab  # noqa: E402

from beeline import gui, logsetup, synth  # noqa: E402

SHOTS = sys.argv[1] if len(sys.argv) > 1 else "/tmp"
errors = []
messagebox.askokcancel = lambda *a, **k: True
messagebox.askyesno = lambda *a, **k: True
messagebox.showerror = lambda title, msg, **k: errors.append("%s: %s" % (title, msg))
messagebox.showinfo = lambda *a, **k: None

logsetup.setup()
app = gui.App()
S = gui.SETUP_SCALE


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        app.update()
        time.sleep(0.02)


def shot(name):
    pump(0.5)
    ImageGrab.grab(xdisplay=os.environ["DISPLAY"]).save(os.path.join(SHOTS, name + ".png"))


def check(cond, msg):
    if not cond:
        print("FAILED:", msg, "| errors:", errors)
        shot("failure")
        cleanup()
        sys.exit(1)
    print("ok:", msg)


def drag(box):
    c = app.setup_canvas
    x, y, w, h = box
    c.event_generate("<ButtonPress-1>", x=int(x * S), y=int(y * S))
    c.event_generate("<B1-Motion>", x=int((x + w) * S), y=int((y + h) * S))
    c.event_generate("<ButtonRelease-1>", x=int((x + w) * S), y=int((y + h) * S))
    pump(0.3)


def click(pt):
    app.setup_canvas.event_generate("<ButtonPress-1>", x=int(pt[0] * S), y=int(pt[1] * S))
    pump(0.2)


def hold_key(keysym, seconds):
    c = app.setup_canvas
    c.focus_force()
    pump(0.2)
    c.event_generate("<KeyPress>", keysym=keysym)
    pump(seconds)
    c.event_generate("<KeyRelease>", keysym=keysym)
    pump(0.3)


game = None


def cleanup():
    if game is not None:
        game.terminate()
    try:
        app.on_close()
    except Exception:
        pass
    app.screen.stop()


pump(1)
shot("01-main")
app.start_screen()
pump(1.5)
# no window manager on the pretend desktop: move the Xephyr window beside Beeline's window
for wid in subprocess.run(["xdotool", "search", "--name", "Beeline hidden screen"], capture_output=True,
                          text=True).stdout.split():
    subprocess.run(["xdotool", "windowmove", wid, "1100", "0"])
check(not errors, "hidden screen started")
state_file = os.path.join(os.environ["BEELINE_DATA"], "game.json")
game = subprocess.Popen([sys.executable, os.path.join(ROOT, "beeline.py"), "--fake-game", "--fast",
                         "--state", state_file], env=dict(os.environ, DISPLAY=app.settings.display))
pump(3)
app.fit_window()
pump(2)
check(not errors and app.last_img is not None, "game window found and preview showing")

# ---- Setup tab, step by step, using the real canvas events
app.children["!notebook"].select(1)
pump(1)
app.set_mode("bag")
click(synth.BAG_LEFT)
click(synth.BAG_RIGHT)
app.capture_bag("empty")
check(app.cal.bag_ready(), "bag meter captured (%s)" % app.step_status["bag"].get())
app.set_mode("eprompt")
drag(synth.EPROMPT_BOX)
app.set_mode("balloon_box")
drag(synth.BALLOON_BOX)
app.capture_balloon(True)          # the fake hive starts with a balloon
app.set_test("eprompt")
shot("02-setup-at-hive")
check("SEEN" in app.test_text.get(), "E-prompt test says SEEN (%s)" % app.test_text.get())

app.start_recording("hive_to_field")
hold_key("d", 5.0)
app.stop_recording()
check("Hive to field: 5" in app.step_status["routes"].get(), "route recorded: " + app.step_status["routes"].get())
pump(1)
app.set_mode("field")
drag(synth.FIELD_BOX)
# Jacob places his Saturator by hand for the sample (the test presses 2 the way a person would;
# Beeline itself can only press 2 through place_sprinkler)
subprocess.run(["xdotool", "key", "2"], env={"DISPLAY": app.settings.display, "PATH": os.environ["PATH"]})
pump(1.5)
app.set_mode("saturator")
drag((610, 370, 60, 60))
app.set_test("saturator")
shot("03-setup-in-field")
check("SEEN" in app.test_text.get(), "Saturator test says SEEN (%s)" % app.test_text.get())
app.set_test("field")
pump(1)
check("YES" in app.test_text.get(), "field test says YES (%s)" % app.test_text.get())

app.start_recording("field_to_hive")
hold_key("a", 5.0)
app.stop_recording()
pump(1.5)
app.set_test("field")
pump(1)
check("no" in app.test_text.get(), "back at hive, field test says no (%s)" % app.test_text.get())
app.save_cal()
check(app.cal.missing("Pine Tree Forest", True) == [], "calibration complete: %s" % app.cal.missing("Pine Tree Forest", True))

# ---- Main tab: dry run first, then a real 2-minute run
app.children["!notebook"].select(0)
app.v_hours.set(0)
app.v_minutes.set(1)
app.v_dry.set(True)
app.start_run()
for _ in range(600):
    pump(0.2)
    if app.runner_thread and not app.runner_thread.is_alive() and app.last_stop_reason != "-":
        break
shot("04-after-dry-run")
check(app.last_stop_reason.startswith("Dry run finished"), "dry run: " + app.last_stop_reason)

app.v_minutes.set(2)
app.v_dry.set(False)
app.last_stop_reason = "-"
app.start_run()
pump(25)
shot("05-running")
for _ in range(1500):
    pump(0.2)
    if app.runner_thread and not app.runner_thread.is_alive() and app.last_stop_reason != "-":
        break
shot("06-finished")
check(app.last_stop_reason.startswith("Finished"), "real run: " + app.last_stop_reason)
import json  # noqa: E402
time.sleep(1.2)
with open(state_file) as f:
    st = json.load(f)
check(st["sprinkler_presses"] == 1 and st["blocked_seen"] == [] and st["left_mid_convert"] == 0,
      "game counters: 2 pressed %d time(s) (1 by the test, 0 by Beeline since it was already placed), "
      "blocked=%s, left mid-convert=%d" % (st["sprinkler_presses"], st["blocked_seen"], st["left_mid_convert"]))
check(app.runner.stats.trips >= 2, "trips: %d" % app.runner.stats.trips)
check(not errors, "no error popups")

# ---- F3 / Stop during a run releases everything
app.v_minutes.set(5)
app.last_stop_reason = "-"
app.start_run()
pump(8)
app.emergency_stop("test")
for _ in range(100):
    pump(0.1)
    if not app.runner_thread.is_alive():
        break
pump(1.5)
with open(state_file) as f:
    st = json.load(f)
check(app.last_stop_reason.startswith("Stopped by you"), "stop button: " + app.last_stop_reason)
check(st["held"] == [] and not st["mouse_held"], "all keys released after Stop")
cleanup()
print("ALL GUI CHECKS PASSED")
