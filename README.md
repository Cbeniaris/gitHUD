# gitHUD

Tired of having to cd into a directory just to run git 
pull every time you switch devices?  Me too, that's why gitHUD now exists. 
gitHUD is a bare-bones terminal UI for the git workflow you actually do day to day:
pull, push, commit, browse status/diff/log. No feature bloat, no GitHub
account integration, just a thin wrapper around the real `git` binary with
a fast repo picker so you never have to `cd` to a repo just to run
`git pull`.

## Install (on each machine -- Fedora and macOS both)

Requires Python 3.10+ and `git` on your PATH (already true on both your
machines).

**From GitHub, editable clone (recommended -- update with `git pull`):**

```bash
git clone https://github.com/yourusername/gitHUD.git
cd gitHUD
pip install -e . --break-system-packages   # Fedora
pip install -e .                            # macOS
```

After the first install, pulling updates is just:

```bash
cd gitHUD && git pull
```

No reinstall needed -- the editable install points straight at the source.

**From GitHub, one-shot install (no local clone kept):**

```bash
pip install git+https://github.com/yourusername/gitHUD.git --break-system-packages
```

Re-run the same command (or add `--upgrade`) to pick up updates.

Either way installs a `gg` command on your PATH -- make sure your pip
script location is on `$PATH` (e.g. `~/.local/bin` on Fedora, or your pip
user-base `bin` on macOS). Prefer full isolation from your system Python?
Swap `pip install` for `pipx install` in any of the commands above.

## Usage

**Register a repo** (do this once per repo, per machine, right after you
clone/create it -- run it from inside the repo):

```bash
cd ~/Documents/some-project
gg --here
```

This adds the repo to `~/.config/githud/repos.json` on that machine.
This file is **not synced** between your Fedora box and your MacBook on
purpose -- paths like `/mnt/drivename/unity/project` on Fedora don't mean
anything on macOS, so each machine keeps its own independent list. Just
run `gg --here` once per repo on each machine you use it from.  

**Launch the picker:**

```bash
gg
```

You'll see every registered repo with its current branch and clean/dirty
status. Pick one and hit enter to work in it.

## Keybinds

### Repo picker
| Key | Action |
|---|---|
| `j`/`k` or arrows | move selection |
| `enter` | open selected repo |
| `a` | add current directory as a repo |
| `d` | remove selected repo from the list |
| `r` | refresh branch/status for all repos |
| `q` | quit |

### Inside a repo
| Key | Action |
|---|---|
| `j`/`k` or arrows | move file selection (diff pane updates to match) |
| `space` | stage/unstage the selected file |
| `a` | stage everything (`git add .`) |
| `c` | open inline commit message bar (enter to confirm, esc to cancel) |
| `p` | push |
| `u` | pull |
| `r` | refresh status/diff/log |
| `q` / `esc` | back to repo picker |

## What this deliberately doesn't do

- No merge conflict resolution UI -- if a pull conflicts, drop to a real
  terminal, resolve it, come back.
- No hunk-level staging -- whole-file stage/unstage only. Add it later if
  you ever actually want it (`git add -p` parsing is the only piece
  that'd need real work).
- No auto-refresh/polling -- press `r` when you want fresh state.
- No Windows support, by design.

## Project layout

```
githud/
├── pyproject.toml
└── githud/
    ├── app.py      # Textual UI: RepoPicker screen, RepoView screen
    ├── git.py       # subprocess wrapper around the real git binary
    └── config.py    # per-machine repos.json load/save
```

`git.py` has zero UI dependencies -- if you ever want a different
frontend, only `app.py` needs to change.
