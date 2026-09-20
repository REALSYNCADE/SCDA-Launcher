# SCDA Launcher

One program for **Splinter Cell: Double Agent — Community Edition**: it gets
you the game if you do not have it, keeps it up to date, and starts it.

## Download

**[⬇ ScdaLauncher.exe](https://github.com/REALSYNCADE/SCDA-Updater/releases/latest/download/ScdaLauncher.exe)**
— that link always serves the newest build.

You only download it once. Keep it anywhere you like.

## Using it

1. Run `ScdaLauncher.exe`. It finds your Community Edition install by itself.
   **No game on this PC?** Press **PLAY** anyway — it offers to download the
   whole game (about 860 MB, 1.7 GB once unpacked) into a folder you pick, then
   carries on.
2. Under **VERSION**, pick one:

   | version | what you get |
   |---|---|
   | **Community Edition** | the standard game: stock 1.1 plus **Kinshasa** as its own map. This is the default. Kinshasa is inside the full download, and an older install receives it on the first PLAY. |
   | **Experimental Build** | Community Edition plus whatever is being tested right now. Expect breakage. |

3. Press **PLAY**. It updates that version if anything is new — Windows may ask
   for administrator rights if the game lives under `Program Files` — and
   then starts the game.
4. New maps are in the map list under their own names. Nothing the game came
   with is replaced: your stock maps stay exactly where they were.

**Close the game first.** The engine keeps its map files locked while it runs,
and the launcher refuses rather than half-patch a running game.

### Settings

| button | what it does |
|---|---|
| **Game folder / Browse** | point the launcher at a game it did not find by itself (the folder with `System\SCDA_Online.exe`) |
| **Check my game** | verifies your files against the ones Community Edition shipped and tells you what can and cannot be installed, without changing anything |
| **Repair / restore stock** | puts back every file the launcher has ever changed and removes every map it added. This is the clean uninstall |
| **Uninstall an add-on** | takes one thing back out. An added map is deleted; a game change is undone and your original file is put back |
| **Download the game** | downloads a fresh copy of the game into a new folder, even if you already have one |

## The versions, in one sentence each

* **Community Edition** is what everybody plays. Kinshasa is in it.
* **Experimental Build** is the playground. Every experimental map is its own
  extra entry in the map list, so the finished version is never replaced. A game
  change from this version can stop you joining a normal match; the launcher
  tells you when one is active, and **Repair / restore stock** takes it all out.

Switching versions never downloads anything and never deletes anything: it is
two small edits to text files, and the launcher keeps every original.

### Windows SmartScreen

The program is not code-signed, so the first run shows *"Windows protected your
PC"*. Click **More info → Run anyway**. If you would rather check first, the
SHA-256 of every file is published in `checksums.txt` on each release.

## What it actually does to your game

* **The full download is checked twice.** The image is refused unless its size
  and SHA-256 match what is published, and the game exe it unpacks is checked
  again afterwards. A broken download resumes where it stopped.
* **A new map only adds.** A few new files plus one line in each of two config
  files. No map, package or setting the game shipped with is overwritten.
* **A game change is always reversible.** Your original is copied aside before
  anything is written, and **Uninstall an add-on** or **Repair / restore stock**
  puts it back byte for byte.
* **Your settings are not touched.** `PlayerProfilePC.ini` and `Default.ini` are
  never part of a release — keybinds, mouse sensitivity, video and gameplay
  options all stay exactly as you have them.
* **If you added your own maps, they survive.** The map list and the map-name
  file are edited, not replaced.
* **Nothing is written until every file has been rebuilt and checked** against
  its published SHA-256. A half-patched game is not a state it can reach.
* **Going back always works.** The first time a file is changed, your original
  is copied to `%LOCALAPPDATA%\SCDA-Launcher\`. That copy is what **Repair /
  restore stock** puts back.

## Trouble

| what you see | what it means |
|---|---|
| *"the download did not match its published hash"* | the file arrived damaged. Run it again — it downloads afresh |
| *"the folder is not empty"* | the game is unpacked into a new folder only. Pick an empty one, or a new name |
| *"the game needs the PhysX system software"* | run the installer it names, inside the game folder under `Installers\PhysX`, then press PLAY again |
| *"needs your original `<file>`, which is missing or already modified"* | a file that map is built from has been changed by something else. **Repair / restore stock**, or download the game again, then update |
| *"map ID N is already used by `<CODE>`"* | another custom map on your install claims the same slot ID. Remove that one first, or ask for a rebuild on a free ID |
| *"no write access"* | run it as administrator (right-click → Run as administrator) |
| *"SCDA is running"* | close the game |
| *"could not reach the update channel"* | no internet, or GitHub is unreachable. On Experimental Build it can also mean there is no experimental build published right now |

## Requirements

Windows, about 2.6 GB of free disk space for a fresh install, and the PhysX
system software (the installer ships inside the game folder).
