# Brief: "Beeline", a safe background Bee Swarm Simulator macro for Linux Mint + Sober

Save this file as `CLAUDE.md` in the repo and keep it updated. Re-read it after any restart.

**Deadline: work until 19:00 UK time today (18:00 UTC).** Keep working right up to then. If you finish the build order early, harden, test and polish. Don't stop early.

---

## 0. Who this is for

I'm Jacob. I'm **not very technical**: I don't follow tool jargon or package names. Everything I have to do myself (installing, running, setting up) must be explained in plain English, step by step, with exact copy-paste commands.

My setup:
- **Linux Mint 21.3 (Cinnamon desktop, X11)** on a desktop PC
- Roblox runs through **Sober** (the Flatpak `org.vinegarhq.Sober`), an unofficial Linux port of the Android Roblox client
- My Roblox username: **Popcat989** (it's shown on my hive in-game)

You're running in the cloud. **You can't run Roblox or see my game.** So design everything to be testable without the game, use calibration on my PC for anything screen-specific, and make the first real-game test as easy and safe as possible.

---

## 0a. ABSOLUTE SAFETY RULES (these beat everything else in this brief)

My account must not be put at risk. The macro must behave like a person at a keyboard and nothing more. (Bee Swarm's developer, Onett, has said macros that just press keys for gathering and farming are fine; what gets accounts banned is cheat software that changes the game. Stay firmly on the right side of that line.)

1. **Input only.** The macro may ONLY: send keyboard key presses, move/click the mouse, and take screenshots of its own display. Nothing else.
2. **Never touch the game itself.** No reading or writing game memory, no injecting code, no executors, no "scripts", no modifying Sober or Roblox files, no network interception, no packet tools, no teleporting. Don't even add code "for later" that does any of this.
3. **No exploits or glitches.** Only normal gameplay. For example, the wiki describes a glitch where leaving the hive before a balloon finishes converting duplicates the balloon. The macro must **always wait for a hive balloon to finish converting** and must never use that or any other glitch.
4. **Blocked keys, enforced in code.** One single function sends every key press, and it refuses anything not on an **allowlist**. Allowed: `w a s d` (move), `space` (jump), `e` (make honey / interact), `shift` (shift lock), `,` and `.` (rotate camera), `i` and `o` (zoom). **Permanently blocked:** number keys `1` and `3`–`0` (my hotbar of boosts and resources), `/` (chat), `Tab`, `Esc`, `` ` ``, `Enter`, `r`, and anything not listed. Since `Esc` and `Enter` are blocked, the macro **can never reset/respawn my character**. In Bee Swarm, respawning is the same as dying: it **loses all the pollen in my bag** and removes my sprinkler (see 0c). Write a test proving blocked keys can never be sent.
   - **The ONE exception: key `2` places my Supreme Saturator.** It must be sent only through its own separate, tightly guarded function, `place_sprinkler()`, never through the normal key function (which keeps refusing `2`). `place_sprinkler()` may press `2` **only when all of these are true**: the macro has confirmed it's standing in the **middle of Pine Tree Forest** at the start of a grind; the Saturator isn't already visible on screen; and it hasn't already placed it this session. **At most once per session by default** (a GUI setting can allow at most one retry if placement visibly failed, never more). Log every press of `2`. Write tests proving `2` can't be sent any other way, can't be sent twice, and can't be sent outside the field.
5. **No clicking my resources.** My items and resources live in the **inventory side panel on the left of the screen**, and there's a hotbar along the bottom. The macro must **never click either of them and never open the inventory or any menu.** Implement this as a **click-safe zone**: clicks are only allowed inside a central rectangle of the game screen (set during calibration, with defaults that keep well away from the left side, the bottom hotbar and the top bar). The one function that clicks refuses anything outside it. Write a test proving this.
6. **Fail safe, never guess.** If anything looks wrong, **stop and release all keys** rather than carry on. For example: the game window isn't found, a Roblox disconnect or "idle" message appears, the screen stops changing for too long, a route takes much longer than recorded, the bag reading makes no sense, the macro has been "walking home" too long, or my character seems to have died and respawned. Log why it stopped.
7. **Emergency stop.** A big Stop button in the GUI, plus a global hotkey (F3) that instantly stops everything and releases every held key.
8. **Time limit.** Every run has a time limit I set, and the macro stops itself when it's up.
9. **Bee Swarm only.** No features for other games.
10. **No secrets.** Never ask for or store my Roblox password or cookies. The macro never logs in and never rejoins servers by itself. I open Sober and join the game myself.
11. **Never type in chat**, and never use GitHub Actions or any cloud service to run the macro. It only ever runs on my own PC.

If any feature would need to break one of these rules, **leave it out** and note it in the progress log.

---

## 0b. Usage limits: keep a wake-up alarm set (do this FIRST, before any other work)

A usage limit could stop this session before 19:00. You can't see it coming, and you can't make a tool call once it hits. So keep a "dead man's switch" running:

1. **Right at the start**, use your scheduling tool (`send_later`, or `ScheduleWakeup`; search your tools for "schedule" if neither shows) to schedule a message back into **this same session** about **45 minutes** from now. The message text:
   `WAKE-UP CHECK: if you were stopped by a usage limit, re-read CLAUDE.md (brief + progress log), check git status, and carry on from the first unticked item until 19:00 UK. If you are already mid-task, ignore this, but make sure a new wake-up is scheduled.`
2. **After every commit**, schedule a fresh wake-up about 45 minutes ahead, and cancel the older one if your tool allows it.
3. **Backup chain:** at the start, also schedule wake-ups at **16:30, 17:15, 18:00 and 18:30 UK**. Extra ones that arrive while you're busy are harmless.
4. **After any restart**, first re-read CLAUDE.md and `git log`, and check that `main` is clean. Never redo work that's already committed.
5. **At about 18:45 UK**, cancel any wake-ups scheduled after 19:00, so nothing restarts the session later.
6. **If no scheduling tool exists in this session**, say so in the first line of the progress log, so I know to restart it by hand.

---

## 0c. Game knowledge you need (researched from the Bee Swarm wiki, Natro Macro docs and community guides)

### The basics
- Bee Swarm Simulator: you walk around **fields** of flowers. You and your bees collect **pollen** into your bag. When the bag's full you go back to your **hive** and convert pollen into **honey**.
- Holding the **left mouse button** swings your tool, which collects pollen from flowers around you.
- **Tokens** (ability boosts, honey, items) appear on the ground in the field and are collected by walking over them. Walking a loop pattern collects them naturally.

### Hives
- A server has **6 hives** in a row. When you join, you claim one by following a red arrow and pressing **E**. My username appears on my hive.
- Natro Macro numbers them **slot 1 to 6: slot 1 is usually nearest the cannon, slot 6 the farthest.** I'll tell the macro my slot during setup, and my hive may be a different slot each time I join a server.
- **Converting:** stand on the pad in front of your hive. An **"E" prompt** appears; pressing **E** starts "Make Honey". Your bees fly between you and the hive converting the bag. Natro detects the on-screen E-prompt image before pressing E. Do the same (calibrate a sample of the prompt). Press E **once**. Don't spam it, since it can toggle converting off.
- **Hive balloon (important for my blue hive):** my Buoyant Bees make blue balloons in the field that fill with pollen and float back to my hive, where they join the **Hive Balloon**. When I convert, the bees **convert my bag first, then the hive balloon**. Fully converting the hive balloon grants **Balloon Blessing** (a big capacity and honey-at-hive buff), and the game shows a message like "🎈 The hive balloon granted you x… of Balloon Blessing!". The hive balloon also slowly shrinks over time if left unconverted. So each trip home: wait until the bag is empty **and** the hive balloon has finished converting (balloon gone / blessing message), then leave. Natro calls this "Convert Balloon". Make it a GUI option (default: always convert the balloon), with a sensible maximum wait.
- **If you die** (e.g. to a mob), your bees return to the hive and you respawn near your hive.

### Pine Tree Forest (my field)
- A **blue** field (mostly blue flowers, some white), **31 × 23 flowers (713 total)**, located past the Honey Bee Gate near the **Badge Bearer's Guild**.
- **Guarded by 2 mantises and the Werewolf.** The wiki says standing in the part of the field **closest to the Sticker Stack** stops the werewolf detecting you. My bees fight mobs automatically, but the macro should favour that side of the field and treat a death as a stop condition.
- Natro's default walking route from the hive to Pine Tree goes via the Polar Bear; community paths also use cannons (e.g. the Red Cannon, or returning via the Blue Cannon). Using a cannon is just walking onto it and pressing **E**, which is allowed. My recorded routes (see section 2) can use whichever I choose.

### My Supreme Saturator (sprinkler)
- I own **The Supreme Saturator**: a single sprinkler with radius 16 flowers that keeps the field's flowers topped up. On the screen it's a giant golden sprinkler through a **neon blue bear head**, so it's very recognisable.
- My Saturator is on **hotbar key `2`**. Pressing `2` while standing in flowers places it (the Sprinkler Builder has a 1-second cooldown and takes about 3 seconds to build). The macro places it **once, in the middle of Pine Tree, at the start of the grind**, using the guarded `place_sprinkler()` function from rule 4. Every other hotbar key stays blocked.
- The wiki says a sprinkler **stays until you place it somewhere else, die, or leave the game.** Walking to the hive and back doesn't remove it, so one placement lasts the whole session. So the macro must **walk** to and from the hive (never reset/respawn), and if I die, the Saturator is gone and the bag's pollen is lost. That's why death = stop.
- **Drift compensation (copy this idea from Natro):** loops in a field slowly drift off over time. Natro's "Field Drift Compensation" uses the Supreme Saturator as an anchor and is recommended **on** for Supreme owners. Do the same: detect the bright neon-blue Saturator on screen and steer my loops back towards it. Fall back to time-based loops if it can't be seen.

### My account and play style
- Blue hive, 45 bees, mostly level 12. Gear: Petal Wand (tool), Coconut Canister (bag), Gummy Mask, Coconut Clogs, Beekeeper's Belt, Supreme Star Amulet with the **Pop Star** passive (it rewards collecting lots of blue tokens and popping bubbles, so a tight loop that sweeps over bubbles and tokens is good).
- Natro guides recommend "Gather with shift lock" **on** for blue hive tools like the Petal Wand.

### Roblox and camera settings Natro relies on (put these in START-HERE.md as one-time setup)
- In Bee Swarm's own Settings: **Camera Mode = Classic** and **Shift Lock Switch = On**. Pressing Shift then locks the camera behind the character, which makes movement predictable.
- **Zoom fully out** before starting.
- Display scaling **100%** (Natro's most common cause of misclicks is wrong scaling). The hidden screen should use a fixed size (e.g. 1280×720 or 1920×1080, your choice) that never changes.
- Movement speed matters: speed buffs (Haste tokens, Bear Morph, oil) make timed routes overshoot. Natro has a "move speed correction" feature for this. At minimum, routes should check for arrival (e.g. the E-prompt at the hive, the Saturator in the field) instead of trusting timings blindly, and stop if arrival isn't confirmed.
- Roblox **disconnects players who are idle for about 20 minutes**. So the macro must **never go more than a few minutes without input**. In the field it's always walking loops and swinging my Petal Wand (holding left mouse), so that's covered. The risky moments are **standing still at the hive** waiting for the bag and a big hive balloon to convert, and any pause. There, keep sending small harmless inputs every minute or two, such as **nudging the camera with `,` then `.`**. Don't walk or jump, because the wiki notes that moving off the hive pad, or big jumps, stop converting. Also detect the disconnect/idle message and stop if it ever appears.

### Prior art you may study for ideas (don't copy code that breaks section 0a)
- **Natro Macro** (github.com/NatroTeam/NatroMacro, open source, AutoHotkey, Windows): the community standard. Its `paths` and `patterns` folders show how it walks routes and gathering loops (e.g. its Pine Tree paths and patterns like "e_lol" and "CornerXSnake"). Use them to understand movement logic and timing, not to copy wholesale.
- **Hostek/bss-macro** (MIT, Linux, runs Sober inside Xephyr on X11): proof the hidden-screen approach works with Sober.
- **painvision/BeeTuxMacro** (MIT, Linux, archived): another Linux take, with "convert when bag full" and background sandbox ideas.

---

## 1. What the macro does

A background macro that grinds Bee Swarm for me while I study on my normal desktop:

- Runs Sober inside a **separate hidden screen**, so my real desktop stays completely free.
- At the start of the grind: walks to the **middle of Pine Tree** and places my Supreme Saturator with `2`, **once** (rule 4).
- In the field: walks in **small loops** around the Saturator (with drift compensation) while **holding the left mouse button** to swing my Petal Wand, collecting pollen, tokens and bubbles. Never stands still for long (Roblox's 20-minute idle kick).
- Watches my **bag (pollen) meter**. When it's nearly full (threshold set in the GUI, default 95%), it **walks** back to my hive, confirms the E-prompt, presses **E** once, waits until the bag is empty **and the hive balloon has converted**, walks back to the field, and repeats.
- Only converts **when it needs to**. Add a safety maximum time per gathering trip as a backstop.
- Stops itself at the end of the time I chose, after a final trip home to convert.

### The GUI (simple, friendly, plain English labels)

- **Field:** dropdown (Pine Tree Forest; design it so more fields can be added later)
- **Run for:** hours and minutes
- **Convert when bag is:** percentage slider (default 95%)
- **Convert hive balloon each trip:** on/off (default on)
- **Loop size:** small / medium
- **My hive slot:** 1–6
- Big **Start** and **Stop** buttons
- A **status line** ("Gathering in Pine Tree – bag 62%", "Walking to hive", "Converting balloon", "Stopped: route took too long")
- A **small live preview** of the hidden screen (a few frames a second)
- A **Setup** tab for calibration and route recording (see below)
- **Session stats:** trips completed, time running, last stop reason

---

## 2. Technical approach (you choose the details, but keep it simple)

- **Language:** Python 3 with Tkinter for the GUI. Both come with Linux Mint, so I install as little as possible. Avoid anything that needs compiling.
- **Hidden screen:** **Xephyr** (a nested X screen) on a spare display number (e.g. `:5`), with Sober launched into it via `DISPLAY=:5 flatpak run org.vinegarhq.Sober`. Use a visible Xephyr window for first tests, with a setting to minimise or hide it later. If Xephyr has problems, Xvfb is the fallback, viewed through the GUI preview.
- **Input:** send keys and mouse **only to the hidden display** (e.g. `xdotool` with `DISPLAY=:5`), so nothing ever lands on my real desktop.
- **Screen reading:** screenshots of the hidden display only, simple pixel/colour checks and small template matches. No OCR or heavy AI needed.
- **Calibration (Setup tab), because you can't see my game:**
  - **Bag meter:** I click the left and right ends of the bag bar on the preview; the macro learns its position and fill colour and shows a live "bag %" so I can confirm.
  - **E-prompt sample:** while standing on my hive pad, I press "Capture E-prompt" so it can recognise it later.
  - **Hive balloon:** capture what "balloon present" vs "balloon gone" looks like near my hive (or detect the Balloon Blessing message), so it knows when converting is truly finished.
  - **Saturator sample:** while in the field next to my placed Saturator, capture it for drift compensation.
  - **Click-safe zone:** shown as a rectangle on the preview, with defaults; I can shrink it but never expand it into the left panel or bottom hotbar.
  - **Route recorder:** I press "Record route", walk from my hive to Pine Tree myself inside the hidden screen, and press "Stop recording". It saves the key presses and timings (allowlisted keys only). Record the return trip the same way. Save routes **per hive slot**. Show the route length so I can sanity-check it.
  - Each calibration step has a **"Test it"** button that shows what the macro sees.
- **Settings** saved to a small file in the repo folder (no personal data beyond my hive slot).
- **Logs** to a plain text file, plus a screenshot saved whenever the macro stops itself, so I can send them to you.

---

## 3. Testing (since you can't run the game)

- **Unit tests** for: the key allowlist (blocked keys can never be sent, including Esc/Enter/r/1–0), the click-safe zone (out-of-zone clicks refused), bag % reading from **synthetic test images** you generate, E-prompt and Saturator template matching on synthetic images, every stop condition, the time limit, the balloon-wait logic, the anti-idle nudges (no gap without input longer than about 2 minutes, including while converting at the hive), the `place_sprinkler()` guards (only `2`, only once, only in the field), and "release all keys on stop".
- **A fake game for dry runs:** a tiny stand-in window that draws a fake bag meter which fills over time, a fake hive with an E-prompt and a balloon that empties after E is pressed, and a fake Saturator. Run the real macro against it on a virtual display in the cloud (if Xvfb/xdotool are available to you) to check the whole loop: gather, walk, convert bag, convert balloon, return, stop on time.
- A **"Dry run" mode** in the GUI: does everything except send inputs, and shows what it *would* press.
- Run all tests before every commit. Don't commit with failing tests.

---

## 4. Build order (tick these off in the progress log as you go, and commit after each)

1. [ ] Wake-up alarms set (section 0b). Repo skeleton, CLAUDE.md, progress log.
2. [ ] Safe input layer: one key function with the allowlist, one click function with the safe zone, release-all-keys, F3 emergency stop. Tests.
3. [ ] Hidden screen manager: start/stop Xephyr, launch Sober into it, find the window, take screenshots. Clear errors if something's missing.
4. [ ] Calibration tools: bag meter, E-prompt, balloon, Saturator, safe zone. Tested on synthetic images.
5. [ ] Gathering: guarded one-time Saturator placement with `2` in the middle of the field, small loops plus holding left mouse inside the safe zone, drift compensation towards the Saturator, stuck-screen check.
6. [ ] Route recorder and replay per hive slot, arrival checks, converting with E, balloon wait.
7. [ ] Main loop: gather, decide, walk home, convert bag and balloon, walk back; time limit; final convert; all stop conditions (including death and disconnect).
8. [ ] GUI: main tab, Setup tab, live preview, status line, stats, dry-run mode.
9. [ ] Fake-game dry run end to end.
10. [ ] **`START-HERE.md`** for me (see section 5).
11. [ ] Hardening: go through section 0a line by line and check every rule against the code. Write the result in the progress log.
12. [ ] Polish and extra tests until 19:00.

---

## 5. `START-HERE.md`: my guide (plain English, no jargon)

Write it as if for someone who's never used a terminal much:
- What to install, with **exact copy-paste commands** for Linux Mint, and what each one does in one short sentence.
- How to download the macro (copy-paste `git clone` command) and start it.
- **One-time game settings:** Camera Mode Classic, Shift Lock Switch on, zoom fully out, display scaling 100%.
- **Every-session setup:** open the macro, start the hidden screen, join Bee Swarm in Sober yourself, claim a hive, set your hive slot in the macro, make sure the **Supreme Saturator is on hotbar slot 2**, then press Start. The macro walks to the middle of Pine Tree and places the Saturator itself, once.
- **First-time calibration walk-through:** bag meter, E-prompt, balloon, Saturator, routes.
- **First test run checklist:** a **dry run**, then a **5-minute supervised run** with the window visible, then 30 minutes, and only then leave it alone. Do this with no speed buffs active the first time.
- **"If something goes wrong"**: what each stop message means and what to do, how to emergency stop, and where the log and stop screenshots are, so I can send them to Claude.
- A short **"What this macro will never do"** list (from section 0a) in plain words, so I can trust it.

---

## 6. Progress log

Keep a **Progress log** section at the bottom of this file: what's done, what's not, any problems, and anything I need to do. Finish the session with a short **"Summary for Jacob"** at the top of the log: what works, what's untested, and exactly what to do first.

### Summary for Jacob
**What works (tested here in the cloud, without Roblox):**
- The whole loop: walk to Pine Tree, place the Saturator once, gather in loops while swinging, walk home when the bag is full, press E once (only when the banner says **Make Honey**), wait until the pollen reads 0 **and** the banner says "Collect Pollen", walk back, repeat, and stop on time after a final convert.
- **It reads the real game layout from your screenshots**, so there's almost nothing to calibrate:
  - pollen numbers (current ÷ capacity, so capacity changes don't matter), checked against the bar
  - the banner text (Make Honey / Fire the Red Cannon / Collect Pollen)
  - the "(from Pine Tree Forest)" notifications
  - the blue-and-white field
  - your neon-cyan Saturator
  
  It ignores neighbours' balloons and never presses E at the cannon. Tested on your 5 screenshots: bag within ±3% on all of them, every banner read correctly, the Saturator found only in the Pine Tree shots.
- All the safety rules: only allowed keys, key 2 once and only in the field, mouse only in the middle (never the menus, hotbar or notifications), STOP/F3 lets go of everything, and it stops itself whenever something looks wrong.
- The practice game (`python3 beeline.py --practice`) now looks like your screenshots, and the real program was run against it end to end with real text reading. 110 automatic tests pass, on the same Python version Mint 21.3 uses.

**What's untested (because I can't run Roblox):**
- Sober inside the hidden screen on your PC, and whether the window is found and fitted.
- The readings on your PC at 1920×1080. They should match the screenshots, but use the **Test it** buttons (or `--check` on a screenshot) to confirm.
- Exact walking in the real game. Arrival checks will stop it if a route doesn't arrive.
- Screenshot 06 (after converting) wasn't attached. Please add it as `screenshots/06-hive-after-convert.png`.

**What to do first:**
1. Follow **START-HERE.md** Part 1 (install, about 5 minutes; this now includes `tesseract-ocr`).
2. Optional but recommended: Step 5, practise with `python3 beeline.py --practice`.
3. Part 2 (open the hidden screen and Sober, join, claim a hive, shift lock on).
4. Part 3: press **Test it** on each Setup step, then record both routes.
5. Part 4: a **dry run**, then a 5-minute run while you watch, with your finger near F3.
6. If anything stops it or looks odd, send Claude `logs/beeline.log`, the newest picture in `logs/stops/`, and the output of `python3 beeline.py --check` on a screenshot.

### Session notes
- Scheduling tool available (`send_later`). Wake-ups set: +45 min rolling, plus 16:30, 17:15, 18:00, 18:30 UK.
- Cloud test environment: Ubuntu 24.04, `/usr/bin/python3.12` with Tk + Pillow 10 (close to Mint 21.3's Python 3.10 + Pillow 9). Code avoids anything newer than Python 3.10 and uses only the standard library + Pillow (no numpy, nothing to compile).
- Tests: `python3 -m unittest discover -s tests` (standard library only, no pytest needed).

### Build order status
- [x] 1. Wake-up alarms, repo skeleton, CLAUDE.md, progress log.
- [x] 2. Safe input layer (`beeline/safety.py`): one allowlisted key path, backend double-check, click-safe zone with hard limits, `release_all`, `SprinklerGuard.place_sprinkler()` for key 2, F3 hotkey (`beeline/hotkey.py`, needs python3-xlib). Tests in `tests/test_safety.py`.
- [x] 3. Hidden screen manager (`beeline/display.py`): Xephyr (visible, can be minimised) or Xvfb, launch Sober with `DISPLAY=:5 flatpak run org.vinegarhq.Sober`, find/fit/focus the Sober window, screenshots via Pillow (ImageMagick `import` fallback). Tested here: Xvfb start/screenshot/stop, and Xephyr nested inside Xvfb.
- [x] 4. Calibration tools: `beeline/vision.py` (bag bar reading, template match, balloon present/gone, Saturator colour blob, field ground colour fingerprint, frozen screen, disconnect dialog), `beeline/config.py` (Settings + Calibration, saved to `settings.json` and `calibration/`), `beeline/senses.py`, `beeline/synth.py` (synthetic screenshots). Tested in `tests/test_vision.py`. (The clickable Setup tab itself is part of step 8.)
- [x] 5. Gathering (`beeline/macro.py` `Runner.gather/place_saturator/drift_correction`): Saturator placed once via `SprinklerGuard`, small/medium loops while holding left mouse at the safe-zone centre, drift compensation towards the Saturator's on-screen anchor (falls back to plain loops if it can't be seen), frozen-screen check.
- [x] 6. Routes (`beeline/routes.py`): recorder (allowlisted keys only, ignores auto-repeat), save/load per hive slot, replay with live safety checks; arrival checks (field ground colour / E-prompt) with a time limit; convert with ONE E press; balloon wait.
- [x] 7. Main loop: gather -> walk home -> convert bag + balloon -> walk back; time limit with a final convert; stops for death (bag suddenly empties / left the field), disconnect dialog, frozen screen, slow routes, overshoot, walking home too long, convert not starting, balloon too slow (stops AT the hive), missing setup. Anti-idle camera nudges (`,` then `.`) every 40 s of no input. Simulated end-to-end in `tests/test_macro.py` with `beeline/fakeworld.py`.
  - **Decision (safety rule 3 beats the brief's on/off option):** in Bee Swarm the hive balloon starts converting automatically once the bag is empty, so walking away at that point is exactly the balloon-duplication glitch. So Beeline ALWAYS waits for the balloon to finish, and if it takes longer than the max wait it stops *at the hive* rather than leaving. The GUI shows "Convert hive balloon each trip" locked on, with an explanation.
- [x] 8. GUI (`beeline/gui.py`, start with `python3 beeline.py`): Main tab (hidden screen buttons, all settings, big START/STOP, status line, live preview ~3 fps, stats, "what it's pressing" box, dry-run tick box ON by default), Setup tab (click/drag calibration on a live preview with overlays, "Test it" for each step, safe-zone box, route recorder that forwards allowlisted keys from the preview to the hidden screen), Log tab. F3 works when Beeline is focused, and everywhere if python3-xlib is installed. Real runs ask for confirmation with a checklist.
- [x] 9. Fake-game end to end (`beeline/fakegame.py`, `tests/test_e2e_fakegame.py`, run with `BEELINE_E2E=1`): real macro + real xdotool input + real screenshots on Xvfb against the fake game. Result: finished on time, 4 trips in 2 minutes, Saturator pressed once, E once per trip, never left mid-convert, no blocked keys, all keys released.
- [x] 10. `START-HERE.md` written (install, download, one-time game settings, every-session steps, calibration walk-through, first test checklist, stop messages table, never-do list). Short `README.md` added.
- GUI end-to-end test added (`tests/test_gui_e2e.py` + `tests/gui_drive.py`, `BEELINE_E2E=1`): drives the real GUI on a pretend desktop with a real Xephyr hidden screen and the fake game inside. It does every Setup step through the real canvas clicks/drags, records both routes by "typing" into the preview, does a dry run, a real 2-minute run (4 trips), then STOP mid-run. All passed. It caught and I fixed a start-up crash I had introduced.
- [x] 11. Hardening: section 0a checked line by line against the code (results below).

### Safety audit (section 0a, checked against the code)
1. **Input only.** All game input goes through `beeline/safety.py` (`SafeInput` → `XdotoolBackend`). The only other X commands are window management in `display.py` (find, move, resize and focus the Sober window, minimise/restore the Xephyr window) and screenshots. A test scans the package to make sure no other file sends keys or clicks. ✅
2. **Never touch the game.** No memory reading, injection, file changes, network or teleport code anywhere. Sober is only launched with `flatpak run`. ✅
3. **No glitches.** `Runner.wait_for_balloon()` always waits for the balloon (3 "gone" readings in a row). If it takes too long, the run stops *at the hive* and never walks off. The fake world counts "left while converting" and every test asserts it is 0. The "convert balloon" on/off option is locked on because of this rule (see the decision under step 7). ✅
4. **Blocked keys.** `ALLOWED_KEYS` is exactly w a s d space e shift , . i o. `SafeInput` refuses everything else before sending, and the backend checks again. Route files with a blocked key are refused when loaded, and the route recorder ignores non-allowlisted keys. **Key 2:** only `SprinklerGuard.place_sprinkler()` can send it (the backend needs a private token). It requires grind start + field confirmed + Saturator not visible + not already placed. Max 1 press, or 2 if the retry setting is on *and* the first visibly failed. Every press is logged as a WARNING. Tests prove 2 can't go through the normal key functions, can't be sent twice, and can't be sent outside the field or after a stop. ✅
5. **No clicking resources.** The mouse only uses the left button, and only inside `SafeZone`. Calibration can shrink the zone but never grow it past the hard limits (25%–85% across, 15%–80% down), and a tampered calibration file is clamped when loaded. While gathering, the mouse is held at the exact screen centre and the pointer is moved at most once per session, so the camera isn't turned. Tests cover this. ✅
6. **Fail safe.** Stops (with keys released, a log line and a screenshot) for: game window missing (checked every 10 s), screenshot failure, disconnect/idle dialog (on screen for 6 s), screen frozen (default 60 s), route not arriving in time (route time × 1.5 + 10 s), speed-buff overshoot, walking home too long, bag suddenly emptying in the field (death), bag reading jumping, leaving the field for 4 checks in a row (death/respawn or wandering), convert not starting, bag taking too long, balloon too slow, any unexpected error, and going 20 minutes past the time limit. Each has a test. ✅
7. **Emergency stop.** Big STOP button. F3 is grabbed on the real desktop *and* the hidden screen (python3-xlib; tested on Xvfb), and also bound in the Beeline window. All three set the stop flag and call `release_all()`. Every input function checks the flag first. ✅
8. **Time limit.** The deadline is checked every gather loop. At the limit it does a final trip home and converts, then stops. Hard stop at limit + 20 min. ✅
9. **Bee Swarm only.** ✅
10. **No secrets.** Nothing logs in, rejoins or stores credentials. The settings file holds only the options and the hive slot. ✅
11. **No chat, no cloud.** `/` and Enter are blocked. There's no `.github` folder or workflows. The macro only runs on Jacob's PC. ✅
- Extra guard added in the audit: input and the hidden screen are refused on display `:0` **and** on whatever display Beeline was opened on (some PCs use `:1` for the desktop).
- [ ] 12. Polish and extra tests (in progress):
  - Tested on **Python 3.10 + Pillow 9.0.1** (the versions Mint 21.3 ships) as well as 3.12: all tests pass.
  - Routes can now be recorded by walking **directly in the hidden screen window** (`beeline/keywatch.py` watches which allowlisted keys are down on the hidden screen; it only reads, never sends). The preview runs at 10 fps while recording.
  - Sober window detection falls back to the biggest visible window on the hidden screen if its title isn't what we expect.
  - "Test everything at once" button; extra day/night samples for the field and the Saturator; "Faster graphics" (Xephyr `-glamor`) tick box.
  - `make-shortcut.sh` adds Beeline to the Menu and Desktop.
  - "Medium" loop is now a 3-row snake (net zero movement, tested).
  - GUI test found a real weakness: before walking home, the macro only re-centred on the Saturator to within 50 px, so small route errors could leave it just off the hive pad, and it stopped (safely) with "walking home took too long". It now re-centres to within ~12 px first. (I also fixed the fake game so movement follows the exact key timing.)
  - The Saturator finder now uses the **biggest single patch** of its colour, so light-blue bubbles elsewhere can't pull the position off (tested).
  - Images go to Tk as PPM data, so **python3-pil.imagetk is no longer needed**. This also avoids an old-Pillow + Tk 9 hang. The fake-game end to end now passes on Python 3.10 + Pillow 9.0.1 as well.
  - Note: `screen_mode: "xvfb"` in settings.json gives a fully invisible hidden screen, but you can't click into it to join the game, so it's only useful for testing. It isn't shown in the GUI.

## INTERRUPT 1 (from Jacob, ~15:29 UTC): real screenshots. These rules now apply on top of everything above
Real Bee Swarm screenshots are in `screenshots/` (01 at hive "Make Honey", 02 Red Cannon, 03/04 gathering in Pine Tree, 05 hive before convert; **06 "after convert" wasn't attached**, so its tests skip until it's added). They were taken on the desktop with Sober's title bar and the taskbar, so **never hard-code pixels**: use proportions of the game area, and be tolerant to scale.
1. **Bag:** the Pollen bar shows `current/capacity` text, and the **capacity changes** (field buffs, Balloon Blessing). bag% = current ÷ capacity. The fill colour changes with fullness, so use the contrast edge **and** OCR of the numbers (Tesseract), cross-check them, and treat a big disagreement as "something's wrong". While gathering, rate text "(+N/sec)" appears. Ground truth: 01 7.2%, 03 3.4%, 04 1.2%, 05 73.3%, 06 0%.
2. **E-prompt is not unique to the hive:** banner text "Make Honey" (hive), "Fire the Red Cannon" (cannon), "To Make Honey, Collect Pollen From Flower Fields" (nothing left to convert, no E box). Only press E when the banner says Make Honey (or the cannon text at that exact point of a route that uses the cannon).
3. **Balloons:** neighbours' balloons are always on screen, so "balloon visible" means nothing. Converting is done when pollen = 0 **and** the banner says "Collect Pollen…" and/or the feed says "hive balloon refreshed/granted… Balloon Blessing". A balloon image check is only an extra signal, and only for a small area in front of MY pad. Keep the nudges and the never-leave-mid-balloon rule.
4. **My hive:** "Popcat989" on the sign and pad. OCR it as an extra check before pressing E.
5. **Pine Tree:** blue and white flowers on green, dark pine trees, mantis timers. The feed shows "(from Pine Tree Forest)". Use feed OCR + pollen rate text + Saturator/field checks for arrival. Ignore the planter, Bloom labels, other players.
6. **Saturator:** a neon-cyan bear head with a gold sprinkler (03 right of centre, 04 left of the planter). Many cyan distractors (tool rings, planter, balloons, bubbles), so use colour + shape/size + persistence across frames. Must be found in 03/04 and not in 01/02/05/06.
7. **Red Cannon:** unpredictable. Walking routes are the default. Any cannon route must confirm arrival in Pine Tree and stop if it can't.
8. **No-click areas:** top-left Roblox buttons, buffs and menu icons; top-centre bars and banner; top-right "?"; bottom-centre hotbar (slot 2 = Sprinkler Builder) plus the ability icons above it and the icon grid to its right; bottom-right feed. Clicks only in the middle.
9. **Camera:** the screenshots have shift lock off. Keep the plan (Classic + Shift Lock + zoom out) and explain it in START-HERE.
To do: remake the practice game to look like these; tests on the real screenshots (bag ±3%, banner text, converting done, Saturator yes/no, in Pine Tree, safe zone clear of no-click areas); update the convert/arrival logic; good calibration defaults from the screenshots; START-HERE (Tesseract install, camera settings).
### Interrupt 1 progress
- [x] `beeline/bss.py`: reads the real layout from proportions of the game area (defaults measured from the screenshots).
  - Pollen: Tesseract OCR with a strict parser (commas must group properly, the number must start the text, current ≤ capacity), so misreads are rejected rather than guessed. It's cross-checked with the bar fill (a column counts as filled if it's colourful or bright, so no fixed fill colour), and a gap of more than 10 points is flagged as a disagreement.
  - Banner classifier (make_honey / cannon / collect); feed parser (field name, balloon messages); blue-field ground check; Saturator = the biggest very-saturated cyan patch of believable size, fill and aspect.
  - `converting_done()` = pollen 0 AND (banner "collect" OR feed balloon message). `in_field_check()` = blue ground AND (feed names Pine Tree OR pollen coming in OR Saturator in view), and False if the feed names another field.
- [x] `tests/test_real_screenshots.py` (17 tests, all pass, also at 1920 wide). Bag within ±3% on all 5, and exact when the OCR reads the numbers. Banner correct on all. Saturator only in 03/04. In Pine Tree only in 03/04. The safe zone (default and the biggest allowed) never overlaps the no-click areas. 06 tests skip until `screenshots/06-hive-after-convert.png` is added.
- Finding: OCR at 1280×720 misreads digits, so the hidden screen will be **1920×1080**.
- [x] Main loop now uses the real-game rules:
  - E is pressed only when the banner reads "Make Honey" (checked right before pressing). A route may press E only when the banner says "Fire the Red Cannon" at that moment, otherwise it stops.
  - Arrival at the hive = banner "Make Honey" or "Collect Pollen". Converting done = pollen 0 + "Collect Pollen" banner (or the feed's balloon message), seen twice in a row. Neighbours' balloons are ignored.
  - Field arrival = blue ground and the feed doesn't name another field. While gathering, the feed naming another field 3 times in a row → stop.
  - Bag = OCR current ÷ capacity, cross-checked with the bar (bar wins on a gap > 4 points; 3 big disagreements in a row → stop).
  - Tesseract is required for real runs. The hidden screen is 1920×1080 and drift tolerances are proportional.
- [x] Practice game redrawn to look like the real game (`beeline/synth_bss.py`): bars with numbers, E box + banner (3 texts), feed, hotbar, menu icons, neighbours' balloons, cyan Saturator with a gold top. Simulated runs use the fake world's "what OCR would read". The end-to-end tests use real Tesseract on it.
- [x] Setup tab: every step is now "Test it" with the screenshot defaults; fine-tuning is optional. START-HERE updated (Tesseract, camera/shift-lock how-to, new Setup steps, new stop messages).
- [x] Saturator must be seen in 2 looks in a row before it counts (one-frame cyan flashes ignored, tested). Drift correction ignores sudden big jumps.
- [x] The Setup picture now outlines the read areas (pollen, banner, feed), the no-click areas in red, and the green click zone. Checked against the real screenshots: they line up.
- Not done: reading "Popcat989" off the hive sign. Pale yellow text on a yellow sign comes out as "PORRIBS" in OCR, so it's unreliable. The hive check is the "Make Honey" banner plus routes recorded per hive slot.
- Re-ran both end-to-end tests with **real Tesseract** at 1920×1080 on the new practice game. Fake game: 4 trips, all counters correct. GUI test: banner/bag/Saturator/field tests read correctly, dry run, real run, Stop and F3 all pass.

### Safety audit, second pass (after Interrupt 1)
- Rule 1/2: the new code (`bss.py`, `senses.py`, `check.py`, `synth_bss.py`, `keywatch.py`) only reads screenshots or keyboard state. Tesseract runs on screenshot crops; nothing touches the game. The source-scan test still passes. ✅
- Rule 3: the balloon wait now uses pollen 0 + "Collect Pollen" banner/feed message (twice in a row), never "a balloon is on screen". Timeout = stop at the hive. ✅
- Rule 4: E is pressed in exactly one place (`Runner.convert`), and only right after the banner reads "Make Honey". A route's E only goes through if the banner says "Fire the Red Cannon" at that moment. Both are tested, plus a test that fails if another E press is ever added. Key 2 is unchanged. ✅
- Rule 5: the safe zone (default and the biggest allowed) is tested against the no-click areas measured on the real screenshots. ✅
- Rule 6: new stops: Tesseract missing, banner not "Make Honey" at the hive, wrong field named in the feed, numbers vs bar disagreeing badly 3 times in a row, Saturator only "seen" for one frame doesn't count. ✅
- Screenshots confirm the Sober window title is "Sober", which `find_game_window()` searches for first.
