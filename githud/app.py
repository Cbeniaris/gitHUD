"""githud: a bare-bones terminal UI for push/pull/commit across
scattered repos on Fedora and macOS.

Usage:
    gg              launch the repo picker
    gg --here       register the current directory as a repo, then exit
"""
from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, RichLog, Static
from rich.text import Text

from . import config, git

def format_status_cell(code: str) -> Text:
        """Turn a 2-char porcelain code into a fixed-position, color-coded cell
        so the indicator never visually shifts between staged/unstaged -- only
        its color and a checkmark change.
        """
        staged = code[0] not in (" ", "?")
        letter = code[0] if code[0] != " " else code[1]
        mark = "\u2713" if staged else " "  # checkmark
        style = "bold green" if staged else "dim"
        return Text(f"{mark} {letter}", style=style)


class RepoPicker(Screen):
    """Landing screen: pick which repo to work in."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "open_repo", "Open", priority=True),
        Binding("a", "add_repo", "Add cwd"),
        Binding("d", "remove_repo", "Remove"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="repo_table", cursor_type="row")
        yield Static("", id="status_line")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "githud"
        table = self.query_one(DataTable)
        table.add_columns("Name", "Branch", "Status")
        self._repos: list[dict] = []
        self.refresh_table()

    def refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self._repos = config.load_repos()
        for repo in self._repos:
            path = repo["path"]
            if not Path(path).expanduser().exists():
                branch, dirty = "?", "missing"
            else:
                branch = git.current_branch(path)
                dirty = "dirty" if git.is_dirty(path) else "clean"
            table.add_row(repo["name"], branch, dirty)
        if not self._repos:
            self.set_status("No repos yet. cd into one and run: gg --here")

    def action_cursor_down(self) -> None:
        self.query_one(DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one(DataTable).action_cursor_up()

    def action_refresh(self) -> None:
        self.refresh_table()
        self.set_status("Refreshed.")

    def action_open_repo(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_row is None or not self._repos:
            return
        repo = self._repos[table.cursor_row]
        path = repo["path"]
        if not Path(path).expanduser().exists():
            self.set_status(f"Path not found: {path}")
            return
        self.app.push_screen(RepoView(repo["name"], path))

    def action_add_repo(self) -> None:
        cwd = str(Path.cwd())
        if not git.is_repo(cwd):
            self.set_status(f"Not a git repo: {cwd}")
            return
        name = Path(cwd).name
        config.add_repo(name, cwd)
        self.refresh_table()
        self.set_status(f"Added {name} ({cwd})")

    def action_remove_repo(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_row is None or not self._repos:
            return
        repo = self._repos[table.cursor_row]
        config.remove_repo(repo["path"])
        self.refresh_table()
        self.set_status(f"Removed {repo['name']}")

    def action_quit(self) -> None:
        self.app.exit()

    def set_status(self, message: str) -> None:
        self.query_one("#status_line", Static).update(message)


class RepoView(Screen):
    """Working view for a single repo: files / diff / log / commit / push / pull."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("up", "cursor_up", "Up", show=False, priority=True),
        Binding("down", "cursor_down", "Down", show=False, priority=True),
        Binding("space", "toggle_stage", "Stage/Unstage"),
        Binding("a", "stage_all", "Stage all"),
        Binding("c", "start_commit", "Commit"),
        Binding("p", "push", "Push"),
        Binding("u", "pull", "Pull"),
        Binding("r", "refresh", "Refresh"),
        Binding("escape", "back", "Back", priority=True),
        Binding("q", "back", "Back"),
    ]

    def __init__(self, name: str, path: str) -> None:
        super().__init__()
        self.repo_name = name
        self.repo_path = path
        self._entries: list[tuple[str, str]] = []
        self._committing = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="top_pane"):
            yield DataTable(id="files_table", cursor_type="row")
            yield RichLog(id="diff_log", highlight=True, markup=False, wrap=True)
        yield RichLog(id="log_log", highlight=True, markup=False, max_lines=200)
        yield Input(placeholder="commit message -- enter to confirm, esc to cancel", id="commit_input")
        yield Static("", id="status_line")
        yield Footer()

    def on_mount(self) -> None:
        self.title = f"{self.repo_name}  ({self.repo_path})"
        table = self.query_one("#files_table", DataTable)
        table.add_columns("St", "File")
        self.query_one("#commit_input", Input).display = False
        self.refresh_all()

    def refresh_all(self) -> None:
        self._entries = git.status(self.repo_path)
        table = self.query_one("#files_table", DataTable)
        table.clear()
        for code, path in self._entries:
            table.add_row(format_status_cell(code), path)   
        log_log = self.query_one("#log_log", RichLog)
        log_log.clear()
        log_log.write(git.log(self.repo_path))
        self.update_diff()

    def update_diff(self) -> None:
        diff_log = self.query_one("#diff_log", RichLog)
        diff_log.clear()
        table = self.query_one("#files_table", DataTable)
        if table.cursor_row is not None and self._entries:
            _, path = self._entries[table.cursor_row]
            diff_log.write(git.diff(self.repo_path, path))
        else:
            diff_log.write("(no file selected)")

    def action_cursor_down(self) -> None:
        self.query_one("#files_table", DataTable).action_cursor_down()
        self.update_diff()

    def action_cursor_up(self) -> None:
        self.query_one("#files_table", DataTable).action_cursor_up()
        self.update_diff()

    def action_toggle_stage(self) -> None:
        table = self.query_one("#files_table", DataTable)
        if table.cursor_row is None or not self._entries:
            return
        code, path = self._entries[table.cursor_row]
        staged = code[0] not in (" ", "?")
        try:
            if staged:
                git.unstage(self.repo_path, path)
            else:
                git.stage(self.repo_path, path)
        except git.GitError as e:
            self.set_status(str(e))
        self.refresh_all()

    def action_stage_all(self) -> None:
        try:
            git.stage_all(self.repo_path)
            self.set_status("Staged all changes (git add .)")
        except git.GitError as e:
            self.set_status(str(e))
        self.refresh_all()

    def action_start_commit(self) -> None:
        commit_input = self.query_one("#commit_input", Input)
        commit_input.display = True
        commit_input.value = ""
        commit_input.focus()
        self._committing = True

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "commit_input":
            return
        message = event.value.strip()
        commit_input = self.query_one("#commit_input", Input)
        commit_input.display = False
        self._committing = False
        self.set_focus(None)
        if not message:
            self.set_status("Commit cancelled (empty message).")
            return
        try:
            git.commit(self.repo_path, message)
            self.set_status(f"Committed: {message}")
        except git.GitError as e:
            self.set_status(f"Commit failed: {e}")
        self.refresh_all()

    def action_push(self) -> None:
        try:
            out = git.push(self.repo_path)
            self.set_status("Pushed." + (f" {out.strip()}" if out.strip() else ""))
        except git.GitError as e:
            self.set_status(f"Push failed: {e}")

    def action_pull(self) -> None:
        try:
            out = git.pull(self.repo_path)
            self.set_status("Pulled." + (f" {out.strip()}" if out.strip() else ""))
        except git.GitError as e:
            self.set_status(f"Pull failed: {e}")
        self.refresh_all()

    def action_refresh(self) -> None:
        self.refresh_all()
        self.set_status("Refreshed.")

    def action_back(self) -> None:
        if self._committing:
            commit_input = self.query_one("#commit_input", Input)
            commit_input.display = False
            self._committing = False
            self.set_focus(None)
            return
        self.app.pop_screen()

    def set_status(self, message: str) -> None:
        self.query_one("#status_line", Static).update(message)

    


class MyGitApp(App):
    CSS = """
    #top_pane {
        height: 1fr;
    }
    #files_table {
        width: 40%;
    }
    #diff_log {
        width: 60%;
        border-left: solid $accent;
    }
    #log_log {
        height: 10;
        border-top: solid $accent;
    }
    #status_line {
        height: 1;
        color: $text-muted;
        padding-left: 1;
    }
    #commit_input {
        display: none;
    }
    """

    def on_mount(self) -> None:
        self.push_screen(RepoPicker())


def main() -> None:
    if "--here" in sys.argv:
        cwd = str(Path.cwd())
        if not git.is_repo(cwd):
            print(f"Not a git repo: {cwd}")
            sys.exit(1)
        name = Path(cwd).name
        config.add_repo(name, cwd)
        print(f"Added '{name}' ({cwd}) to githud.")
        return
    MyGitApp().run()


if __name__ == "__main__":
    main()
