# Beeline

A safe, input-only background macro for Bee Swarm Simulator on Linux Mint, with Roblox running through Sober.

- **New here? Read [START-HERE.md](START-HERE.md).**
- The brief, safety rules and progress log are in [CLAUDE.md](CLAUDE.md).
- Run it: `python3 beeline.py`
- Practise with the pretend game (no Roblox): `python3 beeline.py --practice`
- See what Beeline reads from a screenshot: `python3 beeline.py --check picture.png`
- Real game screenshots used for the defaults and tests: [screenshots/](screenshots/)
- Tests: `python3 -m unittest discover -s tests` (add `BEELINE_E2E=1` to also run the end-to-end tests with the fake game)
