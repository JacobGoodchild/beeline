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
(Filled in at the end of the session.)

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
