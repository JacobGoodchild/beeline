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
sudo apt update && sudo apt install -y git python3-tk python3-pil xdotool xserver-xephyr xvfb python3-xlib x11-utils
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

### Step 2. Download Beeline

```
cd ~ && git clone https://github.com/jacobgoodchild/beeline.git && cd beeline && git checkout claude/clever-noether-tnl7t5
```

This makes a folder called **beeline** in your Home folder.

- If it asks for a GitHub username and password (this happens if the project is private), it's easier to download it from the website instead. Open github.com/jacobgoodchild/beeline in your browser while logged in, pick the branch **claude/clever-noether-tnl7t5** from the branch menu, click the green **Code** button, then **Download ZIP**. Unzip it into your Home folder and rename the folder to **beeline**.
- Once this work has been merged into the main branch, you won't need the `git checkout ...` part.

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

1. In the Roblox menu (the Roblox logo, top left, then **Settings**):
   - **Camera Mode**: **Classic**
   - **Shift Lock Switch**: **On**
2. Your computer's display scaling should be normal (100%). On Mint: **Menu → Display**, and check **User interface scaling** is **Normal**. (The hidden screen always uses its own fixed size, so this matters less than it does for Windows macros, but it's still best.)
3. Put your **Supreme Saturator on hotbar slot 2**. Beeline presses **2** exactly once per session to place it.

### Step 5 (optional, recommended). Practise with the pretend game first

Beeline comes with a **pretend game**: a simple stand-in for Bee Swarm with a bag bar, a hive with an E prompt and a balloon, a blue-and-white field and a Saturator. It has nothing to do with Roblox, so you can try every button with **zero risk** to your account. It keeps its own separate settings, so nothing you do here affects the real setup.

```
cd ~/beeline && python3 beeline.py --practice
```

Then follow Parts 2 to 4 below exactly as written, except click **Open the practice game in it** instead of opening Sober. In the pretend game the hive pad is where you start, the field is straight to the right (hold **D** for about 5 seconds), and the way back is to the left (hold **A**). For the Saturator sample (Setup step D), click inside the hidden screen window and press **2** to place the pretend Saturator yourself. During a run, the macro places it on its own.

---

## Part 2: Every session

1. Start Beeline: `cd ~/beeline && python3 beeline.py`
2. On the **Main** tab, click **Start hidden screen**. A black window titled "Beeline hidden screen" appears. That's the hidden screen.
3. Click **Open Sober in it**. Sober opens inside that window. Log in if Sober asks, then join **Bee Swarm Simulator** yourself, the normal way.
4. Click **Fit game to hidden screen** so the game fills the window exactly.
5. In the game: **claim a hive** (follow the red arrow, press E). Note which slot it is: **slot 1 is the hive nearest the cannon, slot 6 the furthest**.
6. In Beeline, set **My hive slot** to that number.
7. In the game: **zoom the camera fully out** (scroll the mouse wheel, or hold **O**). Press **Shift** once to turn **shift lock on**. (Beeline also holds O for 2 seconds when it starts, just to be sure. Do your Setup samples fully zoomed out too.)
8. Stand on your **hive pad** so the "E Make Honey" prompt shows.
9. Click **Hide window** (or just leave the hidden screen window alone; see the warning below).
10. Choose how long to run for, untick **Dry run** if you want it to play for real, and press **START**.

The macro then walks to the middle of Pine Tree Forest, places your Saturator (once), and starts gathering.

> **Important: hands off the hidden screen window while it runs.** When your mouse is over that window, or you click in it, your real mouse and keyboard go into the game. With shift lock on, just moving your mouse over it turns the camera, which throws off the routes. (Beeline will notice and stop, but it's better to avoid it.) Click **Hide window** before you start, and **Show window** when you want to look. The little live picture on Beeline's Main tab is always safe to watch.

**To stop:** press the big red **STOP** button, or press **F3** anywhere. Every key is let go straight away.

**When you close Beeline**, it asks whether to close the hidden screen and the game too. Choose **No** if you want to open Beeline again and carry on in the same game.

---

## Part 3: First-time setup (calibration)

Beeline can't know what your screen looks like, so you show it once. Everything is on the **Setup** tab. The big picture there is a live view of the hidden screen. Coloured boxes show what's been set up so far.

Do these in order. Press **Save calibration** at the end (and whenever you change something).

**A. Bag (pollen) meter**
1. Stand at your hive with an **empty bag** (just after making honey).
2. Click **Click its two ends**, then click the **left end** of the bag bar in the picture, then the **right end**. Click near the **bottom edge** of the bar, below the numbers.
3. Click **Bag is EMPTY now: capture**.
4. Optional but recommended: later, when your bag is **full**, click **Bag is FULL now: capture**.
5. Click **Test it**. The line under the picture shows what Beeline reads. Check it roughly matches the game as the bag fills.

**B. Make Honey E-prompt**
1. Stand on your hive pad so the E prompt shows.
2. Click **Drag a box around it**, then drag a snug box around the prompt in the picture.
3. **Test it**: it should say SEEN on the pad and "not seen" when you step off.

**C. Hive balloon**
1. Click **Drag a box where it floats**, and drag a box around where your hive balloon sits near your hive.
2. When the balloon **is there**, click **Balloon is THERE: capture**.
3. When it's **gone** (after it's fully converted), click **Balloon GONE: capture**.
4. **Test it** shows "present", "gone" or "unknown".

**D. Supreme Saturator**
1. In Pine Tree Forest, stand next to your placed Saturator (place it yourself just for this).
2. Click **Drag a box around it**, and drag a box around its **neon-blue bear head**.
3. **Test it**: a red cross should appear on the Saturator.

**E. Field ground**
1. Stand in the **middle of Pine Tree Forest**.
2. Click **Drag a box over the flowers**, and drag a box over the flowers around your character. Keep away from the bag bar and buttons.
3. **Test it**: it should say YES in the field and "no" when you're at the hive.

**Night time:** the game gets darker at night, which can confuse steps D and E. If Beeline stops at night saying it isn't in the field, use **Add another sample (e.g. at night)** on steps D and E while it's dark. Beeline then accepts either look.

**Test everything at once** (button at the bottom of the list) shows every reading on one line. It's handy for a final check.

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

**If the game is very slow or jerky in the hidden screen:** tick **Faster graphics** on the Main tab, close Sober, and start the hidden screen again. If the hidden screen then won't start, untick it.

**If "Fit game to hidden screen" can't find Sober:** wait until Sober has fully opened and try again.

What the stop messages mean:

| Message | What happened | What to do |
|---|---|---|
| Setup isn't finished. Still needed: ... | A calibration step is missing | Finish it on the Setup tab and press Save calibration |
| No recorded route ... for hive slot N | No route for this slot | Record both routes for that slot |
| Couldn't see the 'Make Honey' E-prompt | You weren't on the hive pad at Start | Stand on the pad, then Start. If you are on it, redo Setup step B |
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
