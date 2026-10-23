"""The Beeline window: Main tab (start/stop, settings, live preview), Setup tab
(calibration + route recording) and Log tab.  Plain English everywhere."""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw

from . import display, logsetup
from .config import FIELDS, LOGS_DIR, PRACTICE, SCREEN_SIZE, Calibration, Settings
from .hotkey import GlobalHotkey, xlib_available
from .keywatch import KeyWatcher
from .macro import Runner
from .routes import ROUTE_NAMES, Route, RouteRecorder
from .safety import (ALLOWED_KEYS, InputRefused, RecordingBackend, SafeInput, SafeZone,
                     XdotoolBackend)
from .senses import Senses
from . import bss
from .tkimage import to_photo

log = logging.getLogger("beeline.gui")

W, H = SCREEN_SIZE
MAIN_SCALE = 0.25    # 480 x 270 preview on the Main tab
SETUP_SCALE = 1 / 3  # 640 x 360 preview on the Setup tab

# Tk key names -> Beeline key names (only allowlisted keys; anything else is ignored)
TK_KEYS = {"w": "w", "a": "a", "s": "s", "d": "d", "space": "space", "e": "e",
           "Shift_L": "shift", "Shift_R": "shift", "comma": ",", "period": ".", "i": "i", "o": "o",
           "W": "w", "A": "a", "S": "s", "D": "d", "E": "e", "I": "i", "O": "o"}

BIG = ("TkDefaultFont", 14, "bold")
MED = ("TkDefaultFont", 11)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Beeline PRACTICE - pretend game, no Roblox" if PRACTICE else "Beeline - Bee Swarm macro")
        self.geometry("1080x760")
        self.minsize(960, 700)
        self.settings = Settings.load()
        if PRACTICE and self.settings.display == ":5":
            self.settings.display = ":6"  # keep practice separate from the real hidden screen
        self.cal = Calibration.load()
        self.screen = display.HiddenScreen(self.settings.display, SCREEN_SIZE, self.settings.screen_mode,
                                           glamor=self.settings.xephyr_glamor)
        self.status_q: "queue.Queue[str]" = queue.Queue()
        self.inputs_q: "queue.Queue[str]" = queue.Queue()
        self.runner: Runner | None = None
        self.runner_thread: threading.Thread | None = None
        self.inp: SafeInput | None = None
        self.stop_event = threading.Event()
        self.last_img: Image.Image | None = None
        self.run_started = None
        self.trips = 0
        self.last_stop_reason = "-"
        # setup tab interaction state
        self.mode = None          # what a click/drag on the setup preview means
        self.drag_start = None
        self.drag_rect = None
        self.bag_pts: list = []
        self.test_text = tk.StringVar(value="")
        self.testing = None
        self.recorder: RouteRecorder | None = None
        self.record_inp: SafeInput | None = None
        self._pending_release: dict = {}
        self.keywatch: KeyWatcher | None = None
        self._forwarded: set = set()
        self.watch_q: "queue.Queue" = queue.Queue()

        self._build()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.bind_all("<F3>", lambda e: self.emergency_stop("F3"))
        self.hotkey = GlobalHotkey(self._hotkey_pressed, displays=(None,))
        if self.hotkey.start() and display.display_is_up(self.settings.display):
            self.hotkey.add_display(self.settings.display)
        self.after(1500, self._show_hotkey)
        self.after(200, self._tick_preview)
        self.after(100, self._tick_queues)
        self.after(1000, self._tick_stats)

    # ================================================================ layout
    def _build(self) -> None:
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.main_tab = ttk.Frame(nb, padding=10)
        self.setup_tab = ttk.Frame(nb, padding=10)
        self.log_tab = ttk.Frame(nb, padding=10)
        nb.add(self.main_tab, text="  Main  ")
        nb.add(self.setup_tab, text="  Setup  ")
        nb.add(self.log_tab, text="  Log  ")
        self._build_main()
        self._build_setup()
        self._build_log()

    def _build_main(self) -> None:
        f = self.main_tab
        left = ttk.Frame(f)
        left.pack(side="left", fill="y", padx=(0, 12))
        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True)

        self.v_glamor = tk.BooleanVar(value=self.settings.xephyr_glamor)
        box = ttk.LabelFrame(left, text="1. Hidden screen", padding=8)
        box.pack(fill="x", pady=(0, 8))
        ttk.Button(box, text="Start hidden screen", command=self.start_screen).pack(fill="x")
        ttk.Button(box, text="Open the practice game in it" if PRACTICE else "Open Sober in it",
                   command=self.open_sober).pack(fill="x", pady=2)
        ttk.Button(box, text="Fit game to hidden screen", command=self.fit_window).pack(fill="x")
        ttk.Checkbutton(box, text="Faster graphics (try this if the game is slow;\n restart the hidden screen after changing)",
                        variable=self.v_glamor, command=self._glamor_changed).pack(anchor="w")
        row = ttk.Frame(box)
        row.pack(fill="x", pady=(2, 0))
        ttk.Button(row, text="Hide window", command=lambda: self.screen.set_xephyr_window_visible(False)
                   ).pack(side="left", expand=True, fill="x")
        ttk.Button(row, text="Show window", command=lambda: self.screen.set_xephyr_window_visible(True)
                   ).pack(side="left", expand=True, fill="x")

        box = ttk.LabelFrame(left, text="2. Settings", padding=8)
        box.pack(fill="x", pady=(0, 8))
        self.v_field = tk.StringVar(value=self.settings.field)
        self.v_hours = tk.IntVar(value=self.settings.run_hours)
        self.v_minutes = tk.IntVar(value=self.settings.run_minutes)
        self.v_convert = tk.IntVar(value=self.settings.convert_percent)
        self.v_balloon = tk.BooleanVar(value=True)
        self.v_loop = tk.StringVar(value=self.settings.loop_size)
        self.v_slot = tk.IntVar(value=self.settings.hive_slot)
        self.v_dry = tk.BooleanVar(value=self.settings.dry_run)
        self.v_retry = tk.BooleanVar(value=self.settings.allow_sprinkler_retry)
        self.v_drift = tk.BooleanVar(value=self.settings.drift_compensation)
        self.v_zoom = tk.BooleanVar(value=self.settings.zoom_out_at_start)

        def row(label):
            r = ttk.Frame(box)
            r.pack(fill="x", pady=2)
            ttk.Label(r, text=label, width=24).pack(side="left")
            return r
        ttk.Combobox(row("Field:"), textvariable=self.v_field, values=FIELDS, state="readonly",
                     width=20).pack(side="left")
        r = row("Run for:")
        ttk.Spinbox(r, from_=0, to=12, textvariable=self.v_hours, width=4).pack(side="left")
        ttk.Label(r, text="hours ").pack(side="left")
        ttk.Spinbox(r, from_=0, to=59, textvariable=self.v_minutes, width=4).pack(side="left")
        ttk.Label(r, text="minutes").pack(side="left")
        r = row("Convert when bag is:")
        self.convert_label = ttk.Label(r, text="%d%%" % self.v_convert.get(), width=5)
        ttk.Scale(r, from_=50, to=100, variable=self.v_convert, length=130,
                  command=lambda v: (self.v_convert.set(int(float(v))),
                                     self.convert_label.config(text="%d%%" % int(float(v))))).pack(side="left")
        self.convert_label.pack(side="left")
        r = row("Convert hive balloon:")
        ttk.Checkbutton(r, text="always (locked on)", variable=self.v_balloon, state="disabled").pack(side="left")
        r = row("Loop size:")
        ttk.Radiobutton(r, text="small", value="small", variable=self.v_loop).pack(side="left")
        ttk.Radiobutton(r, text="medium", value="medium", variable=self.v_loop).pack(side="left")
        r = row("My hive slot (1 = by cannon):")
        ttk.Spinbox(r, from_=1, to=6, textvariable=self.v_slot, width=4,
                    command=self.refresh_setup_status).pack(side="left")
        ttk.Checkbutton(box, text="Drift compensation (steer back towards the Saturator)",
                        variable=self.v_drift).pack(anchor="w")
        ttk.Checkbutton(box, text="Zoom the camera fully out at the start (holds O for 2 seconds)",
                        variable=self.v_zoom).pack(anchor="w")
        ttk.Checkbutton(box, text="Allow ONE retry if placing the Saturator visibly fails",
                        variable=self.v_retry).pack(anchor="w")
        ttk.Checkbutton(box, text="Dry run (practice: presses NOTHING, shows what it would press)",
                        variable=self.v_dry).pack(anchor="w", pady=(4, 0))

        box = ttk.Frame(left)
        box.pack(fill="x", pady=4)
        self.start_btn = tk.Button(box, text="START", font=BIG, bg="#3a9d3a", fg="white",
                                   activebackground="#4cb84c", height=2, command=self.start_run)
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 4))
        self.stop_btn = tk.Button(box, text="STOP  (F3)", font=BIG, bg="#c62828", fg="white",
                                  activebackground="#e53935", height=2,
                                  command=lambda: self.emergency_stop("Stop button"))
        self.stop_btn.pack(side="left", expand=True, fill="x")

        self.status_var = tk.StringVar(value="Ready. Finish the Setup tab first, then press Start.")
        ttk.Label(right, textvariable=self.status_var, font=BIG, wraplength=520).pack(anchor="w")
        self.preview = tk.Canvas(right, width=int(W * MAIN_SCALE), height=int(H * MAIN_SCALE), bg="black",
                                 highlightthickness=0)
        self.preview.pack(anchor="w", pady=6)
        self.stats_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.stats_var, font=MED, justify="left").pack(anchor="w")
        ttk.Label(right, text="What it's pressing (in a dry run: what it WOULD press):").pack(anchor="w", pady=(8, 0))
        self.inputs_box = tk.Text(right, height=7, width=60, state="disabled", font=("TkFixedFont", 9))
        self.inputs_box.pack(anchor="w", fill="x")
        self.hotkey_var = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.hotkey_var, foreground="#555").pack(anchor="w", pady=(6, 0))

    def _build_setup(self) -> None:
        f = self.setup_tab
        left = ttk.Frame(f)
        left.pack(side="left", fill="both")
        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        self.setup_help = tk.StringVar(value="Pick a step on the right. The picture below is the hidden screen.")
        ttk.Label(left, textvariable=self.setup_help, font=MED, wraplength=640, foreground="#1a4f8b"
                  ).pack(anchor="w")
        self.setup_canvas = tk.Canvas(left, width=int(W * SETUP_SCALE), height=int(H * SETUP_SCALE),
                                      bg="black", highlightthickness=3, highlightbackground="#888",
                                      takefocus=1)
        self.setup_canvas.pack(pady=6)
        self.setup_canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.setup_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.setup_canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.setup_canvas.bind("<KeyPress>", self.on_record_key_press)
        self.setup_canvas.bind("<KeyRelease>", self.on_record_key_release)
        self.setup_canvas.bind("<FocusIn>", lambda e: self.setup_canvas.config(highlightbackground="#2e7d32"))
        self.setup_canvas.bind("<FocusOut>", lambda e: self.setup_canvas.config(highlightbackground="#888"))
        ttk.Label(left, textvariable=self.test_text, font=MED, wraplength=640).pack(anchor="w")
        self.tools_var = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.tools_var, foreground="#555", justify="left").pack(anchor="w", pady=6)

        canvas = tk.Canvas(right, highlightthickness=0)
        scroll = ttk.Scrollbar(right, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.step_status: dict = {}

        def step(key, title):
            lf = ttk.LabelFrame(inner, text=title, padding=6)
            lf.pack(fill="x", pady=3)
            v = tk.StringVar(value="")
            ttk.Label(lf, textvariable=v, foreground="#2e7d32", wraplength=360, justify="left").pack(anchor="w")
            self.step_status[key] = v
            return lf

        def btns(parent, *items):
            r = ttk.Frame(parent)
            r.pack(fill="x", pady=1)
            for text, cmd in items:
                ttk.Button(r, text=text, command=cmd).pack(side="left", padx=1)

        s = step("bag", "A. Bag (pollen) numbers and bar")
        btns(s, ("Test it", lambda: self.set_test("bag")),
             ("Fine-tune: click the bar's two ends", lambda: self.set_mode("bag")))
        s = step("eprompt", "B. Banner (Make Honey / cannon / Collect Pollen)")
        btns(s, ("Test it", lambda: self.set_test("eprompt")))
        s = step("balloon", "C. Converting finished (bag + hive balloon)")
        btns(s, ("Test it", lambda: self.set_test("balloon")),
             ("Optional: box in front of MY pad", lambda: self.set_mode("balloon_box")))
        btns(s, ("My balloon THERE: capture", lambda: self.capture_balloon(True)),
             ("My balloon GONE: capture", lambda: self.capture_balloon(False)))
        s = step("saturator", "D. Supreme Saturator")
        btns(s, ("Test it", lambda: self.set_test("saturator")),
             ("Fine-tune: drag a box around it", lambda: self.set_mode("saturator")))
        btns(s, ("Add another sample (e.g. at night)", lambda: self.set_mode("saturator_add")))
        s = step("field", "E. In Pine Tree Forest?")
        btns(s, ("Test it", lambda: self.set_test("field")))
        s = step("zone", "F. Click-safe zone (green box)")
        btns(s, ("Drag a smaller box", lambda: self.set_mode("zone")), ("Reset to default", self.reset_zone))
        s = step("routes", "G. Routes for your hive slot")
        btns(s, ("Record: hive -> field", lambda: self.start_recording("hive_to_field")),
             ("Record: field -> hive", lambda: self.start_recording("field_to_hive")))
        btns(s, ("STOP recording + save", self.stop_recording), ("Cancel recording", self.cancel_recording))
        ttk.Button(inner, text="Test everything at once", command=lambda: self.set_test("all")).pack(fill="x", pady=(6, 0))
        ttk.Button(inner, text="Save calibration", command=self.save_cal).pack(fill="x", pady=6)
        self.refresh_setup_status()
        tools = display.tool_status()
        tools["python3-xlib (F3 from anywhere)"] = xlib_available()
        self.tools_var.set("Installed helpers:\n" + "\n".join(
            ("  OK   " if ok else "  MISSING  ") + name for name, ok in tools.items()))

    def _build_log(self) -> None:
        f = self.log_tab
        self.log_box = tk.Text(f, state="disabled", font=("TkFixedFont", 9))
        self.log_box.pack(fill="both", expand=True)
        r = ttk.Frame(f)
        r.pack(fill="x", pady=4)
        ttk.Button(r, text="Open logs folder", command=self.open_logs).pack(side="left")
        ttk.Label(r, text="Logs and stop screenshots are in: " + LOGS_DIR).pack(side="left", padx=8)

    # ================================================================ settings
    def read_settings(self) -> Settings:
        s = self.settings
        try:
            s.field = self.v_field.get()
            s.run_hours = int(self.v_hours.get())
            s.run_minutes = int(self.v_minutes.get())
            s.convert_percent = int(self.v_convert.get())
            s.loop_size = self.v_loop.get()
            s.hive_slot = int(self.v_slot.get())
        except (tk.TclError, ValueError):
            raise ValueError("One of the settings isn't a number. Please check 'Run for' and 'hive slot'.")
        s.convert_balloon = True
        s.dry_run = bool(self.v_dry.get())
        s.allow_sprinkler_retry = bool(self.v_retry.get())
        s.drift_compensation = bool(self.v_drift.get())
        s.zoom_out_at_start = bool(self.v_zoom.get())
        s.validate()
        s.save()
        return s

    # ================================================================ hidden screen
    def start_screen(self) -> None:
        try:
            self.screen.start()
            self.status_var.set("Hidden screen is running on %s. Now press 'Open Sober in it'." % self.screen.display)
            self.hotkey.add_display(self.screen.display)
            self.after(1500, self._show_hotkey)
        except display.DisplayError as e:
            messagebox.showerror("Hidden screen", str(e))

    def _glamor_changed(self) -> None:
        self.settings.xephyr_glamor = bool(self.v_glamor.get())
        self.settings.save()
        self.screen.glamor = self.settings.xephyr_glamor

    def _show_hotkey(self) -> None:
        if not xlib_available():
            self.hotkey_var.set("F3 works while this window is focused. Install python3-xlib for F3 everywhere.")
            return
        on = ", ".join(self.hotkey.active_on) or "only this window so far"
        self.hotkey_var.set("F3 emergency stop active on: %s" % on)

    def open_sober(self) -> None:
        if PRACTICE:
            if not display.display_is_up(self.screen.display):
                messagebox.showerror("Practice", "Start the hidden screen first.")
                return
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            env = dict(os.environ, DISPLAY=self.screen.display)
            self.screen.sober_proc = subprocess.Popen([sys.executable, os.path.join(root, "beeline.py"),
                                                       "--fake-game"], env=env)
            self.status_var.set("Practice game opening. Then press 'Fit game to hidden screen'.")
            return
        try:
            self.screen.launch_sober()
            self.status_var.set("Sober is opening in the hidden screen. Join Bee Swarm and claim a hive yourself.")
        except display.DisplayError as e:
            messagebox.showerror("Sober", str(e))

    def fit_window(self) -> None:
        try:
            self.screen.fit_game_window()
            self.status_var.set("Game window fitted to the hidden screen.")
        except display.DisplayError as e:
            messagebox.showerror("Game window", str(e))

    def grab(self) -> Image.Image | None:
        try:
            if display.display_is_up(self.screen.display):
                return self.screen.screenshot()
        except Exception:
            return None
        return None

    # ================================================================ running
    def start_run(self) -> None:
        if self.runner_thread and self.runner_thread.is_alive():
            return
        try:
            s = self.read_settings()
        except ValueError as e:
            messagebox.showerror("Settings", str(e))
            return
        if self.recorder is not None:
            messagebox.showerror("Busy", "Stop the route recording first.")
            return
        if not display.display_is_up(s.display):
            messagebox.showerror("Hidden screen", "Start the hidden screen and join Bee Swarm first.")
            return
        window_alive = None
        if not s.dry_run:
            if self.screen.find_game_window() is None:
                messagebox.showerror("Game window", "Couldn't find the Sober window on the hidden screen.")
                return
            if not messagebox.askokcancel(
                    "Start for real?",
                    "Beeline will now press keys in the hidden screen for %dh %dm.\n\n"
                    "Checklist:\n - You're standing on your hive pad (slot %d)\n"
                    " - Shift lock is ON, camera zoomed fully out\n"
                    " - Supreme Saturator is on hotbar slot 2\n - No speed buffs (first runs)\n\n"
                    "Press F3 or STOP at any time." % (s.run_hours, s.run_minutes, s.hive_slot)):
                return
            try:
                self.screen.fit_game_window()
            except display.DisplayError as e:
                messagebox.showerror("Game window", str(e))
                return

            def window_alive():
                return self.screen.find_game_window() is not None
        routes = {n: Route.load(s.hive_slot, n, s.field) for n in ROUTE_NAMES}
        self.stop_event = threading.Event()
        backend = RecordingBackend() if s.dry_run else XdotoolBackend(s.display)
        self.inp = SafeInput(backend, SCREEN_SIZE, self.cal.zone(), stop_event=self.stop_event,
                             dry_run=s.dry_run)
        prefix = "[dry run] would press: " if s.dry_run else ""
        self.inp.on_input = lambda what: self.inputs_q.put(time.strftime("%H:%M:%S ") + prefix + what)
        self.runner = Runner(s, self.cal, self.inp, self.screen.screenshot, routes,
                             status=self.status_q.put, window_alive=window_alive)
        self.run_started = time.monotonic()
        self.runner_thread = threading.Thread(target=self._run_thread, daemon=True)
        self.runner_thread.start()
        self.start_btn.config(state="disabled")
        log.info("run started (dry run=%s, slot=%d, %dh%dm)", s.dry_run, s.hive_slot, s.run_hours, s.run_minutes)

    def _run_thread(self) -> None:
        reason = self.runner.run()
        self.status_q.put("__done__" + reason)

    def _hotkey_pressed(self) -> None:
        """Runs on the F3 listener thread.  Stops input straight away (thread-safe) and
        tells the window via the queue (Tk must only be touched from its own thread)."""
        log.warning("EMERGENCY STOP (F3)")
        self.stop_event.set()
        for inp in (self.inp, self.record_inp):
            if inp is not None:
                try:
                    inp.release_all()
                except Exception:
                    log.exception("release_all failed")
        self.status_q.put("__f3__")

    def emergency_stop(self, source: str = "Stop") -> None:
        log.warning("EMERGENCY STOP (%s)", source)
        self.stop_event.set()
        for inp in (self.inp, self.record_inp):
            if inp is not None:
                try:
                    inp.release_all()
                except Exception:
                    log.exception("release_all failed")
        if self.recorder is not None:
            self.cancel_recording()
        if self.runner_thread is not None and self.runner_thread.is_alive():
            self.status_var.set("Stopping... (%s)" % source)
        else:
            self.status_var.set("Stopped (%s). All keys released." % source)

    # ================================================================ periodic updates
    def _tick_queues(self) -> None:
        self._drain_watch()
        try:
            while True:
                msg = self.status_q.get_nowait()
                if msg == "__f3__":
                    self.emergency_stop("F3")
                elif msg.startswith("__done__"):
                    self.last_stop_reason = msg[8:]
                    self.status_var.set(self.last_stop_reason)
                    self.trips = self.runner.stats.trips if self.runner else self.trips
                    self.run_started = None
                    self.start_btn.config(state="normal")
                else:
                    self.status_var.set(msg)
        except queue.Empty:
            pass
        lines = []
        try:
            while True:
                lines.append(self.inputs_q.get_nowait())
        except queue.Empty:
            pass
        if lines:
            self.inputs_box.config(state="normal")
            self.inputs_box.insert("end", "\n".join(lines) + "\n")
            self.inputs_box.delete("1.0", "end-200l")
            self.inputs_box.see("end")
            self.inputs_box.config(state="disabled")
        loglines = []
        try:
            while True:
                loglines.append(logsetup.gui_queue.get_nowait())
        except queue.Empty:
            pass
        if loglines:
            self.log_box.config(state="normal")
            self.log_box.insert("end", "\n".join(loglines) + "\n")
            self.log_box.delete("1.0", "end-3000l")
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(150, self._tick_queues)

    def _tick_stats(self) -> None:
        trips = self.runner.stats.trips if self.runner else self.trips
        if self.run_started is not None:
            secs = int(time.monotonic() - self.run_started)
            running = "%d:%02d:%02d" % (secs // 3600, secs // 60 % 60, secs % 60)
        else:
            running = "not running"
        self.stats_var.set("Trips completed: %d\nTime running: %s\nLast stop reason: %s"
                           % (trips, running, self.last_stop_reason))
        self.after(1000, self._tick_stats)

    def _tick_preview(self) -> None:
        img = self.grab()
        if img is not None:
            self.last_img = img
            small = img.resize((int(W * MAIN_SCALE), int(H * MAIN_SCALE)), Image.BILINEAR)
            self._main_photo = to_photo(small, self)
            self.preview.delete("all")
            self.preview.create_image(0, 0, anchor="nw", image=self._main_photo)
            self._draw_setup_preview(img)
        else:
            self.preview.delete("all")
            self.preview.create_text(int(W * MAIN_SCALE) // 2, int(H * MAIN_SCALE) // 2, fill="white",
                                     text="Hidden screen not running")
        # about 3 frames a second normally, 10 while recording a route
        self.after(100 if self.recorder is not None else 300, self._tick_preview)

    def _draw_setup_preview(self, img: Image.Image) -> None:
        over = img.copy()
        d = ImageDraw.Draw(over)
        c = self.cal
        z = SafeZone.from_dict(c.safe_zone).to_pixels(W, H)
        d.rectangle(z, outline=(0, 255, 0), width=3)
        if c.bag_left and c.bag_right:
            d.line((tuple(c.bag_left), tuple(c.bag_right)), fill=(255, 0, 255), width=3)
        for p in self.bag_pts:
            d.ellipse((p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5), outline=(255, 0, 255), width=2)
        for box, col in ((c.eprompt_box, (255, 255, 0)), (c.balloon_box, (0, 200, 255)),
                         (c.field_box, (255, 128, 0))):
            if box:
                x, y, w, h = box
                d.rectangle((x, y, x + w, y + h), outline=col, width=2)
        self._update_test(img, d)
        small = over.resize((int(W * SETUP_SCALE), int(H * SETUP_SCALE)), Image.BILINEAR)
        self._setup_photo = to_photo(small, self)
        self.setup_canvas.delete("img")
        self.setup_canvas.create_image(0, 0, anchor="nw", image=self._setup_photo, tags="img")
        self.setup_canvas.tag_lower("img")

    # ================================================================ setup: tests
    def set_test(self, what) -> None:
        self.testing = what
        self.setup_help.set("Testing: watch the line under the picture. It updates live.")

    def _update_test(self, img, d) -> None:
        what = getattr(self, "testing", None)
        if not what:
            return
        # reading text (OCR) takes a moment, so only re-test every 1.5 seconds
        now = time.monotonic()
        if now - getattr(self, "_last_test", 0) < 1.5 and getattr(self, "_last_test_what", None) == what:
            self._draw_test_marks(d)
            return
        self._last_test, self._last_test_what = now, what
        senses = Senses(self.cal, self.v_field.get())
        self._marks = []
        try:
            if not senses.ocr_ready() and what in ("bag", "eprompt", "all", "field"):
                self.test_text.set("The text reader isn't installed. Run: sudo apt install tesseract-ocr "
                                   "(the bar and Saturator still work without it)")
            if what == "bag":
                b = senses.bag(img)
                self.test_text.set("Bag reads: %s   (numbers: %s, bar: %d%%)%s" % (
                    "?" if b.percent is None else "%.1f%%" % b.percent,
                    "{:,}/{:,}".format(b.current, b.capacity) if b.current is not None else "not read",
                    b.bar_percent or 0, "   NUMBERS AND BAR DISAGREE" if b.disagree else ""))
            elif what == "eprompt":
                banner = senses.banner(img)
                self.test_text.set("Banner: %s" % {
                    "make_honey": "'Make Honey' (on my hive pad, OK to press E)",
                    "collect": "'Collect Pollen...' (at the hive, nothing left to convert)",
                    "cannon": "'Fire the Red Cannon' (NOT the hive: E won't be pressed)",
                    "": "nothing readable"}[banner])
            elif what == "balloon":
                self.test_text.set("Converting finished: %s   |   my balloon spot (optional): %s" % (
                    "YES" if senses.converting_done(img) else "no", senses.balloon_state(img)))
            elif what == "saturator":
                b = senses.saturator(img)
                self.test_text.set("Saturator: %s" % ("SEEN (red cross), size %dx%d" % (b.w, b.h)
                                                        if b.visible() else "not seen"))
                if b.visible():
                    self._marks = [(b.cx, b.cy)]
            elif what == "all":
                s = senses.look(img)
                self.test_text.set(
                    "Bag: %s (%s)  |  Banner: %s  |  Converting done: %s  |  Saturator: %s  |  "
                    "In field: %s (%s)  |  Disconnect box: %s" % (
                        "-" if s.bag is None else "%.1f%%" % s.bag, s.bag_source, s.banner or "-",
                        "YES" if s.converting_done else "no", "SEEN" if s.saturator else "no",
                        "YES" if s.in_field else "no", s.in_field_reason, "YES" if s.dialog else "no"))
                if s.saturator:
                    self._marks = [s.saturator_xy]
            elif what == "field":
                ok, why = senses.field_confirmed(img)
                blue, green = senses.reader.ground_scores(img)
                self.test_text.set("In %s: %s (%s; blue flowers %.0f%%, green %.0f%%)" % (
                    senses.field_name, "YES" if ok else "no", why, blue * 100, green * 100))
        except Exception as e:
            self.test_text.set("Test failed: %s" % e)
        self._draw_test_marks(d)

    def _draw_test_marks(self, d) -> None:
        r = int(W * 0.015)
        for (x, y) in getattr(self, "_marks", []):
            d.line((x - r, y, x + r, y), fill=(255, 0, 0), width=6)
            d.line((x, y - r, x, y + r), fill=(255, 0, 0), width=6)

    # ================================================================ setup: capturing
    HELP = {
        "bag": "Click the LEFT end of the pollen bar, then the RIGHT end. Click near the bottom edge of "
               "the bar, below the numbers.",
        "eprompt": "Stand on your hive pad so the E 'Make Honey' prompt shows, then drag a box tightly around it.",
        "balloon_box": "Optional. Drag a small box just in front of YOUR pad where your own balloon floats "
                       "(not the neighbours' balloons).",
        "saturator": "Stand next to your placed Saturator, then drag a box around its neon-cyan bear head.",
        "field": "Stand in the middle of the field, then drag a box over the flowers around your character "
                 "(avoid the bag bar and buttons).",
        "saturator_add": "Extra sample: stand next to your Saturator (e.g. at night) and drag a box around its "
                         "bear head. The first sample is kept.",
        "field_add": "Extra sample: stand in the middle of the field (e.g. at night) and drag a box over the "
                     "flowers. Earlier samples are kept.",
        "zone": "Drag a box for where the mouse may click. It can only be made smaller, never bigger "
                "than the allowed area.",
    }

    def set_mode(self, mode) -> None:
        self.mode = mode
        self.testing = None
        self.bag_pts = []
        self.setup_help.set(self.HELP.get(mode, ""))

    def _to_screen(self, e) -> tuple:
        return (int(e.x / SETUP_SCALE), int(e.y / SETUP_SCALE))

    def on_canvas_press(self, e) -> None:
        self.setup_canvas.focus_set()
        if self.mode == "bag":
            self.bag_pts.append(self._to_screen(e))
            if len(self.bag_pts) == 2:
                l, r = sorted(self.bag_pts)
                self.cal.bag_left, self.cal.bag_right = list(l), list(r)
                if self.last_img is not None:
                    self.cal.capture_bag(self.last_img, l, r)
                self.setup_help.set("Bar position fine-tuned. Press 'Test it' to check the reading.")
                self.mode = None
                self.refresh_setup_status()
            else:
                self.setup_help.set("Now click the RIGHT end of the bag bar.")
            return
        if self.mode:
            self.drag_start = (e.x, e.y)
            self.setup_canvas.delete("drag")

    def on_canvas_drag(self, e) -> None:
        if self.drag_start and self.mode:
            self.setup_canvas.delete("drag")
            self.setup_canvas.create_rectangle(self.drag_start[0], self.drag_start[1], e.x, e.y,
                                               outline="red", width=2, tags="drag")

    def on_canvas_release(self, e) -> None:
        if not (self.drag_start and self.mode):
            return
        x0, y0 = self.drag_start
        self.drag_start = None
        self.setup_canvas.delete("drag")
        x0, x1 = sorted((x0, e.x))
        y0, y1 = sorted((y0, e.y))
        box = [int(x0 / SETUP_SCALE), int(y0 / SETUP_SCALE),
               max(4, int((x1 - x0) / SETUP_SCALE)), max(4, int((y1 - y0) / SETUP_SCALE))]
        img = self.last_img
        if img is None:
            messagebox.showerror("Setup", "The hidden screen isn't showing anything yet.")
            return
        mode, self.mode = self.mode, None
        if mode == "eprompt":
            self.cal.capture_eprompt(img, box)
            self.setup_help.set("E-prompt captured. Press 'Test it' to check it's recognised.")
        elif mode == "balloon_box":
            self.cal.balloon_box = box
            self.setup_help.set("Balloon area set. Now capture it with the balloon THERE, and later GONE.")
        elif mode in ("saturator", "saturator_add"):
            self.cal.capture_saturator(img, box, add=(mode == "saturator_add"))
            self.setup_help.set("Saturator captured (%d sample(s)). Press 'Test it'." % len(self.cal.saturator_colours()))
        elif mode in ("field", "field_add"):
            self.cal.capture_field(img, box, self.v_field.get(), add=(mode == "field_add"))
            self.setup_help.set("Field ground captured (%d sample(s)). Press 'Test it' here, then again near your "
                                "hive (should say no)." % len(self.cal.field_samples(self.v_field.get())))
        elif mode == "zone":
            x, y, w, h = box
            self.cal.set_safe_zone(x / W, y / H, (x + w) / W, (y + h) / H)
            self.setup_help.set("Click-safe zone set (kept inside the allowed area).")
        self.refresh_setup_status()

    def capture_bag(self, which) -> None:
        if not (self.cal.bag_left and self.cal.bag_right):
            messagebox.showinfo("Bag meter", "First click 'Click its two ends'.")
            return
        if self.last_img is None:
            return
        self.cal.capture_bag(self.last_img, self.cal.bag_left, self.cal.bag_right, which)
        self.setup_help.set("Bag captured (%s). Press 'Test it' and compare with the game." % which)
        self.refresh_setup_status()

    def capture_balloon(self, present) -> None:
        if not self.cal.balloon_box:
            messagebox.showinfo("Balloon", "First drag a box where the balloon floats.")
            return
        if self.last_img is None:
            return
        self.cal.capture_balloon(self.last_img, self.cal.balloon_box, present)
        self.setup_help.set("Balloon %s sample captured." % ("THERE" if present else "GONE"))
        self.refresh_setup_status()

    def reset_zone(self) -> None:
        self.cal.safe_zone = SafeZone().to_dict()
        self.refresh_setup_status()

    def save_cal(self) -> None:
        self.cal.save()
        self.refresh_setup_status()
        messagebox.showinfo("Saved", "Calibration saved.")

    def refresh_setup_status(self) -> None:
        if not hasattr(self, "step_status"):
            return
        c = self.cal
        fieldname = self.v_field.get() if hasattr(self, "v_field") else FIELDS[0]
        ok = lambda b: "done" if b else "NOT DONE"
        default = "Uses the defaults from your screenshots"
        self.step_status["bag"].set("fine-tuned" if c.layout.get("pollen_bar") else default)
        self.step_status["eprompt"].set(default + (" (reads text: OK)" if bss.ocr_available()
                                                   else ". NEEDS: sudo apt install tesseract-ocr"))
        self.step_status["balloon"].set(default + ("; my balloon spot: there=%s, gone=%s" % (
            ok(c.balloon_present_img is not None), ok(c.balloon_gone_img is not None)) if c.balloon_box else ""))
        self.step_status["saturator"].set("fine-tuned (hue %s)" % (c.saturator_hue,) if c.saturator_hue else default)
        self.step_status["field"].set(default)
        z = c.zone()
        self.step_status["zone"].set("Zone: %.0f%%-%.0f%% across, %.0f%%-%.0f%% down"
                                     % (z.left * 100, z.right * 100, z.top * 100, z.bottom * 100))
        try:
            slot = int(self.v_slot.get())
        except Exception:
            slot = self.settings.hive_slot
        parts = []
        for name, label in ROUTE_NAMES.items():
            try:
                r = Route.load(slot, name, fieldname)
            except Exception as e:
                r = None
                log.warning("route file problem: %s", e)
            parts.append("%s: %s" % (label, r.summary() if r else "NOT RECORDED"))
        self.step_status["routes"].set("Slot %d:\n" % slot + "\n".join(parts))

    # ================================================================ setup: route recording
    def start_recording(self, name) -> None:
        if self.runner_thread and self.runner_thread.is_alive():
            messagebox.showerror("Busy", "Stop the macro first.")
            return
        if not display.display_is_up(self.settings.display):
            messagebox.showerror("Hidden screen", "Start the hidden screen first.")
            return
        try:
            slot = int(self.v_slot.get())
        except Exception:
            return
        self.record_stop = threading.Event()
        self.record_inp = SafeInput(XdotoolBackend(self.settings.display), SCREEN_SIZE, self.cal.zone(),
                                    stop_event=self.record_stop)
        self.recorder = RouteRecorder(name, slot, self.v_field.get())
        # Also watch the hidden screen's keyboard, so walking directly in the hidden screen
        # window is recorded too.  When this works it is the ONLY source of recorded keys
        # (keys typed on the preview are forwarded to the game and then seen here).
        self.keywatch = KeyWatcher(self.settings.display,
                                   lambda k, d: self.watch_q.put((k, d, time.monotonic())))
        if not self.keywatch.start():
            self.keywatch = None
        self.mode = None
        self.testing = None
        self.setup_canvas.focus_set()
        where = "on your hive pad" if name == "hive_to_field" else "in the middle of the field (by the Saturator)"
        how = ("Walk in the hidden screen window, or click this picture and walk here"
               if self.keywatch else "Click this picture and walk here")
        self.setup_help.set("RECORDING '%s' for slot %d. Start %s. %s with W A S D (Space, Shift, comma and "
                            "full stop also work). Press 'STOP recording + save' when you arrive."
                            % (ROUTE_NAMES[name], slot, where, how))

    def _tk_key(self, e):
        return TK_KEYS.get(e.keysym)

    def on_record_key_press(self, e) -> None:
        if self.recorder is None:
            return
        key = self._tk_key(e)
        if key is None:
            return
        pending = self._pending_release.pop(key, None)
        if pending is not None:          # auto-repeat: a release immediately followed by a press
            self.after_cancel(pending)
            return
        if key in self._forwarded:
            return
        try:
            self.record_inp.key_down(key)
            self._forwarded.add(key)
            if self.keywatch is None:
                self.recorder.key(key, True)
        except InputRefused:
            pass

    def on_record_key_release(self, e) -> None:
        if self.recorder is None:
            return
        key = self._tk_key(e)
        if key is None:
            return
        self._pending_release[key] = self.after(40, self._finish_release, key)

    def _finish_release(self, key) -> None:
        self._pending_release.pop(key, None)
        if self.recorder is None:
            return
        self.record_inp.key_up(key)
        self._forwarded.discard(key)
        if self.keywatch is None:
            self.recorder.key(key, False)

    def stop_recording(self) -> None:
        if self.recorder is None:
            return
        for k in list(self._pending_release):
            self.after_cancel(self._pending_release.pop(k))
        self.record_inp.release_all()
        self._forwarded.clear()
        if self.keywatch is not None:
            self.keywatch.stop()
            time.sleep(0.05)
            self._drain_watch()
            self.keywatch = None
        route = self.recorder.stop()
        self.recorder = None
        if not route.events:
            messagebox.showinfo("Route", "Nothing was recorded. Click the picture first so it has the keyboard.")
            return
        path = route.save()
        log.info("route saved: %s (%s)", path, route.summary())
        self.setup_help.set("Saved '%s': %s." % (ROUTE_NAMES[route.name], route.summary()))
        self.refresh_setup_status()

    def _drain_watch(self) -> None:
        try:
            while True:
                k, d, t = self.watch_q.get_nowait()
                if self.recorder is not None:
                    self.recorder.key(k, d, at=t)
        except queue.Empty:
            pass

    def cancel_recording(self) -> None:
        if self.keywatch is not None:
            self.keywatch.stop()
            self.keywatch = None
        self._forwarded.clear()
        if self.record_inp is not None:
            self.record_inp.release_all()
        self.recorder = None
        self._pending_release.clear()
        self.setup_help.set("Recording cancelled.")

    # ================================================================ misc
    def open_logs(self) -> None:
        os.makedirs(LOGS_DIR, exist_ok=True)
        subprocess.Popen(["xdg-open", LOGS_DIR], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def on_close(self) -> None:
        self.emergency_stop("window closed")
        self.hotkey.stop()
        if self.runner_thread and self.runner_thread.is_alive():
            self.runner_thread.join(timeout=3)
        if self.screen.server_proc is not None and display.display_is_up(self.screen.display):
            if messagebox.askyesno("Close Beeline", "Also close the hidden screen (and the game inside it)?\n\n"
                                   "Choose No to leave the game running, so you can open Beeline again "
                                   "and carry on."):
                self.screen.stop()
        self.destroy()


def main() -> None:
    path = logsetup.setup()
    log.info("Beeline starting; log file: %s", path)
    app = App()
    app.mainloop()
