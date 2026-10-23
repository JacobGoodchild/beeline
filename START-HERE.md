# Beeline: start here

Beeline plays Bee Swarm Simulator for you in the background while you get on with other things. It runs the game on a **separate hidden screen**, so your normal desktop stays free. It gathers in Pine Tree Forest, walks home when your bag is full, makes honey, waits for your hive balloon, walks back, and repeats until the time you set runs out.

It only does what a person at a keyboard could do: it presses a few keys and holds the left mouse button. Nothing more. (See [What Beeline will never do](#what-beeline-will-never-do) at the bottom.)

This guide assumes you've barely used a terminal. Wherever you see a grey box, copy the whole thing and paste it into the terminal.

> **How to paste into the terminal:** open the terminal with **Ctrl + Alt + T**. To paste, press **Ctrl + Shift + V** (plain Ctrl + V doesn't work in the terminal). Then press **Enter**. If it asks for your password, type your normal Linux login password. You won't see anything appear as you type it; that's normal. Then press Enter.

---

## Part 1: One-time install (about 5 minutes)

### Step 1. Install the helper programs

Paste this into the terminal:

```
sudo apt update && sudo apt install -y git python3-tk python3-pil xdotool xserver-xephyr xvfb python3-xlib x11-utils tesseract-ocr
```

What each one is for:
- **git**: downloads Beeline from GitHub.
- **python3-tk**: lets Beeline show its window.
- **python3-pil**: lets Beeline look at screenshots of the game.
- **xdotool**: sends key presses, but only to the hidden screen, never to your real desktop.
- **xserver-xephyr**: the hidden screen, shown as a normal window you can see, minimise and close.
- **xvfb**: a fully invisible hidden screen (a backup option).
- **python3-xlib**: lets **F3** stop Beeline even when its window isn't the one in front.
- **x11-utils**: a small tool Beeline uses to check the hidden screen is running.
- **tesseract-ocr**: a text reader. Beeline uses it to read the pollen numbers ("2,348,365/32,442,211"), the banner under them ("Make Honey" or "Fire the Red Cannon") and the messages in the bottom-right corner ("from Pine Tree Forest"). **Beeline won't start a real run without it**, because it never presses E unless the banner says Make Honey.

### Step 2. Download Beeline

```
cd ~ && git clone https://github.com/jacobgoodchild/beeline.git && cd beeline
```

This makes a folder called **beeline** in your Home folder.

- If it asks for a GitHub username and password (this happens if the project is private), it's easier to download it from the website instead. Open github.com/jacobgoodchild/beeline in your browser while logged in click the green **Code** button, then **Download ZIP**. Unzip it into your Home folder and rename the folder to **beeline**.

### Step 3. Start Beeline

```
cd ~/beeline && python3 beeline.py
```

The Beeline window opens. Use this same command every time you want to start it.

**Optional: add a Beeline icon** to your Menu (under Games) and your Desktop, so you don't need the terminal next time:

```
sh ~/beeline/make-shortcut.sh
```

(The first time you double-click the desktop icon, Mint may ask whether to trust it. Choose **Trust and Launch**.)

**To get updates later** (when Claude has improved it), close Beeline, then paste:

```
cd ~/beeline && git pull
```

### Step 4. One-time game settings

Do these yourself in the game (Beeline never opens menus):

1. In the game, open the Roblox menu: click the **Roblox logo** in the top-left corner (or the **≡** button next to it), then the **Settings** tab. Change:
   - **Camera Mode**: **Classic**
   - **Shift Lock Switch**: **On**

   Close the menu. Now pressing **Shift** once turns **shift lock** on: the mouse pointer disappears, a small lock icon shows, and the camera stays behind your character so walking is predictable. Press Shift again to turn it off. (In your screenshots the pointer was visible, so shift lock was off then. Turn it on before recording routes and before every run.)

   Beeline still works with shift lock **off**, as long as it's the same as when you recorded your routes. With it **on**, though, the camera can't drift away by accident, so that's the recommended way. Beeline never presses Shift itself unless your recorded route did.
2. Your computer's display scaling should be normal (100%). On Mint: **Menu → Display**, and check **User interface scaling** is **Normal**. (The hidden screen always uses its own fixed size, so this matters less than it does for Windows macros, but it's still best.)
3. Put your **Supreme Saturator on hotbar slot 2**. Beeline presses **2** exactly once per session to place it.

### Step 5 (optional, recommended). Practise with the pretend game first

Beeline comes with a **pretend game**, a simple stand-in drawn to look like your Bee Swarm screenshots. It has Honey and Pollen bars with numbers, the E box with "Make Honey", a hive with neighbours' balloons, a blue-and-white field, a cyan Saturator and messages in the corner. It has nothing to do with Roblox, so you can try every button with **zero risk** to your account. It keeps its own separate settings, so nothing you do here affects the real setup.

```
cd ~/beeline && python3 beeline.py --practice
```

Then follow Parts 2 to 4 below exactly as written, except click **Open the practice game in it** instead of opening Sober. In the pretend game the hive pad is where you start, the field is straight to the right (hold **D** for about 5 seconds), and the way back is to the left (hold **A**). To try Setup step D before a run, click inside the hidden screen window and press **2** in the field to place the pretend Saturator. During a run, the macro places it on its own if it isn't there yet.

---

## Part 2: Every session

1. Start Beeline: `cd ~/beeline && python3 beeline.py`
2. On the **Main** tab, click **Start hidden screen**. A black window titled "Beeline hidden screen" appears. That's the hidden screen. It's 1920×1080 (big enough for Beeline to read the numbers clearly), so it may not fit on your monitor. That's fine; you can hide it.
3. Click **Open Sober in it**. Sober opens inside that window. Log in if Sober asks, then join **Bee Swarm Simulator** yourself, the normal way.
4. Click **Fit game to hidden screen** so the game fills the window exactly.
5. In the game: **claim a hive** (follow the red arrow, press E). Note which slot it is: **slot 1 is the hive nearest the cannon, slot 6 the furthest**.
6. In Beeline, set **My hive slot** to that number.
7. In the game: **zoom the camera fully out** (scroll the mouse wheel, or hold **O**). Press **Shift** once to turn **shift lock on**. (Beeline also holds O for 2 seconds when it starts, just to be sure. Do your Setup checks fully zoomed out too.)
8. Stand on your **hive pad** so the banner at the top says "E Make Honey" (not "Fire the Red Cannon").
9. Click **Hide window** (or just leave the hidden screen window alone; see the warning below).
10. Choose how long to run for, untick **Dry run** if you want it to play for real, and press **START**.

The macro then walks to the middle of Pine Tree Forest, places your Saturator (once), and starts gathering.

> **Important: hands off the hidden screen window while it runs.** When your mouse is over that window, or you click in it, your real mouse and keyboard go into the game. With shift lock on, just moving your mouse over it turns the camera, which throws off the routes. (Beeline will notice and stop, but it's better to avoid it.) Click **Hide window** before you start, and **Show window** when you want to look. The little live picture on Beeline's Main tab is always safe to watch.

**To stop:** press the big red **STOP** button, or press **F3** anywhere. Every key is let go straight away.

**When you close Beeline**, it asks whether to close the hidden screen and the game too. Choose **No** if you want to open Beeline again and carry on in the same game.

---

## Part 3: First-time setup (checking what Beeline sees)

Beeline already knows what Bee Swarm looks like. It learned the layout from your screenshots: the Honey and Pollen bars at the top, the E box and banner, the hotbar, the notifications in the bottom-right corner, and your neon-cyan Saturator. So there's very little to set up. You mostly just **check** each reading with its **Test it** button on the **Setup** tab. The big picture there is a live view of the hidden screen. The line under it shows the answer, and it updates every second or two.

**0. Interface size (do this first).** The Setup picture outlines where Beeline reads things: **pink** around the Pollen numbers, **yellow** around the banner, **orange** around the corner messages. Red boxes are places it never clicks, and the green box is where clicks are allowed. Roblox may draw its buttons and bars a little bigger or smaller in the hidden screen than in your screenshots. If the pink and yellow boxes don't sit on the Pollen numbers and the banner, drag the **Interface size** slider until they do, then press **Save calibration**.

**A. Bag (pollen).** Click **Test it**. It shows the percentage, the numbers it read (e.g. 2,348,365/32,442,211) and what the bar looks like. It always uses current ÷ capacity, so it doesn't matter that your capacity changes in the field or after a Balloon Blessing. If the numbers and the bar ever disagree a lot, Beeline stops rather than guess. *Only if the reading is wrong:* click **Fine-tune: click the bar's two ends**, then click the left end and the right end of the pollen bar in the picture, near its bottom edge.

**B. Banner.** On your hive pad, **Test it** should say **'Make Honey'**. At the Red Cannon it says **'Fire the Red Cannon'** (Beeline never presses E there). When everything is converted, it says **'Collect Pollen...'**.

**C. Converting finished.** Beeline knows converting (bag **and** your hive balloon) is finished when the pollen reads 0 **and** the banner changes to "To Make Honey, Collect Pollen From Flower Fields" (or the corner says the hive balloon gave you a Balloon Blessing). It doesn't look at balloons, because your neighbours' balloons are always on screen. *Optional:* if you want an extra check, drag a small box just in front of **your own** pad where your balloon floats, and capture it there and gone.

**D. Supreme Saturator.** In Pine Tree with your Saturator placed, **Test it** should say SEEN and put a red cross on it. *Only if it doesn't:* use **Fine-tune: drag a box around it**.

**E. In Pine Tree Forest?** In the middle of the field, **Test it** should say YES. It checks for blue and white flowers on the ground, plus one of these: the corner messages say "from Pine Tree Forest", pollen is coming in, or your Saturator is in view. At your hive it should say no.

**Night time:** if the darker night-time colours ever confuse the Saturator check, add a night sample with **Add another sample (e.g. at night)**.

**Test everything at once** (at the bottom of the list) shows every reading on one line. Press **Save calibration** if you fine-tuned anything.

**F. Click-safe zone** (the green box)
The mouse is only ever allowed inside this box. The default is already safe: it keeps well away from your inventory on the left, the hotbar at the bottom and the top bar. You can drag a **smaller** box if you like. It can never be made bigger than the allowed area.

**G. Routes** (do this for each hive slot you use)
1. Stand on your hive pad. Turn shift lock on. Don't touch the camera.
2. Click **Record: hive -> field**.
3. Walk to the **middle of Pine Tree Forest** using **W A S D** (Space, Shift, comma and full stop work too). You can walk in either place:
   - **in the hidden screen window** (easiest, because it's full size and smooth): click inside it first so it has your keyboard, **or**
   - **on the Setup picture**: click it once so it gets a green border, then walk. The picture updates 10 times a second while recording. Use the route you like, cannons included (walk onto one and press E). It helps to end slightly towards the **Sticker Stack** side of the middle, where the werewolf doesn't notice you.
4. Click **STOP recording + save** the moment you arrive.
5. Now, from the middle of the field, click **Record: field -> hive**, click the picture, walk home to your hive pad, and click **STOP recording + save**.
6. The Setup tab shows each route's length, for example "38.2 seconds, 14 key presses". If it looks wrong, record it again.

Only allowed keys are recorded. Anything else you press is ignored and never sent.

Tips for good routes:
- Record **field -> hive** starting right next to your Saturator, in the spot where you placed it (that's where Beeline stands before walking home).
- Finish **hive -> field** in the middle of the field, and finish **field -> hive** standing on the hive pad with the E prompt showing.
- Walk in a few long straight lines rather than lots of little taps. Long straight walks replay more reliably.
- Don't move the mouse over the game while recording (with shift lock on, that turns the camera, and turns aren't recorded).

---

## Part 4: Your first test runs

Please do these in order, with **no speed buffs** active (no Haste, Bear Morph or oil) the first few times:

1. **Dry run.** Leave **Dry run** ticked and press START, standing on your hive pad. Beeline presses **nothing**. It reads the screen and lists what it **would** press in the box on the Main tab. When it finishes, it says what it would have stopped for, if anything.
2. **5-minute supervised run.** Untick Dry run, set **Run for** to 0 hours 5 minutes, keep the hidden screen window **visible** (but don't touch it), and watch. Your finger should be near **F3**.
3. **30-minute run**, checking in now and then.
4. Only then, leave it running alone.

---

## Part 5: If something goes wrong

**Emergency stop:** the red **STOP** button, or **F3**. It lets go of every key immediately.

**Where the evidence is:** the **logs** folder inside the beeline folder (the **Open logs folder** button on the Log tab opens it).
- `logs/beeline.log`: everything Beeline did, with times.
- `logs/stops/`: a screenshot from every time Beeline stopped itself.

Send those to Claude if you want help.

**Check what Beeline reads from a screenshot.** Take a screenshot of the game (on Mint, press **PrtSc**; it's saved in your **Pictures** folder), then paste this, changing the file name:

```
cd ~/beeline && python3 beeline.py --check ~/Pictures/your-screenshot.png
```

It prints the bag %, the banner, whether it sees your Saturator, and whether it thinks you're in Pine Tree. Copy that text to Claude. It works on normal desktop screenshots of the Sober window too.

**One screenshot still wanted:** your hive pad just after converting has *completely* finished (pollen 0, banner "To Make Honey, Collect Pollen From Flower Fields"). Save it as `screenshots/06-hive-after-convert.png` in the beeline folder. The tests for it switch on automatically.

**If the game is very slow or jerky in the hidden screen:** tick **Faster graphics** on the Main tab, close Sober, and start the hidden screen again. If the hidden screen then won't start, untick it.

**If "Fit game to hidden screen" can't find Sober:** wait until Sober has fully opened and try again.

What the stop messages mean:

| Message | What happened | What to do |
|---|---|---|
| The text reader (Tesseract) isn't installed | Beeline can't read the banner or numbers | Run `sudo apt install tesseract-ocr`, then start Beeline again |
| The notifications say I'm gathering in ... Field | The route ended in the wrong field | Re-record the hive -> field route |
| No recorded route ... for hive slot N | No route for this slot | Record both routes for that slot |
| Couldn't see the 'Make Honey' prompt | You weren't on your hive pad at Start (or you were at the cannon) | Stand on your pad so the banner says Make Honey, then Start. Check with Setup step B |
| Not on my hive pad (the banner doesn't say Make Honey) | The walk home ended somewhere else, e.g. the cannon | E is never pressed there. Re-record the field -> hive route |
| Route to the field took too long | The walk didn't end up in the field | Usually a speed buff, the camera got turned, or the wrong hive slot. Check the slot, turn the camera back, re-record the route |
| Walking home took too long | Didn't reach the hive pad | As above, for the field-to-hive route |
| Bag suddenly emptied in the field | Your character probably died (the bag empties when you die) | Check the game. The Saturator is gone too, so start a new run from your hive |
| No longer in Pine Tree Forest | Wandered off, or died and respawned | Check the game; re-record routes if it keeps happening |
| Bag reading makes no sense | The bag number jumped strangely | Redo Setup step A |
| The screen hasn't changed for N seconds | The game froze or disconnected | Check Sober; rejoin yourself if needed |
| Roblox disconnect / idle message | Roblox showed a disconnect box | Rejoin yourself (Beeline never rejoins on its own) |
| The game window disappeared | Sober closed or crashed | Reopen Sober and rejoin |
| Converting didn't start after pressing E | Pressing E didn't start honey-making | Check you're on the pad; redo Setup step B |
| Stopped at the hive: the balloon was still converting | The balloon took longer than the maximum wait | Nothing is lost. Your bees keep converting. Start again when it's done |
| Couldn't see the hidden screen | The hidden screen closed | Press Start hidden screen again, reopen Sober |
| Stopped by you | You pressed STOP or F3 | - |
| Finished: time limit reached | All done, with a final trip home to make honey | - |

---

## What Beeline will never do

- Press any key except: **W A S D**, **Space**, **E**, **Shift**, **,** and **.** (turn the camera), **I** and **O** (zoom).
- Press your hotbar keys **1, 3, 4, 5, 6, 7, 8, 9, 0**. It presses **2** only once per session, to place your Saturator in the middle of the field.
- Press **Esc**, **Enter**, **R**, **Tab**, **/** or **`**. So it can **never reset your character**, open menus or type in chat.
- Click your inventory on the left, your hotbar, or any menu. The mouse stays inside the safe green box.
- Touch the game itself: no cheats, no scripts, no reading or changing game memory or files, no teleporting, no glitches.
- Leave your hive while the hive balloon is still converting. (Leaving early is a known glitch, so Beeline always waits.)
- Log in, rejoin servers, or ask for your password or cookies.
- Run anywhere except on your own computer.

If anything looks wrong, Beeline stops and lets go of every key rather than guessing.
