"""
Git Manager Plugin
Provides Git repository management for the Minecraft server folder.
Allows initializing, committing, viewing history, and managing branches.
"""
import gi
import os
import gettext
import subprocess
import threading

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

_ = gettext.gettext

from plugins.base_plugin import BasePlugin


class GitManagerPlugin(BasePlugin):
    """Git repository management plugin for Minecraft server directories."""

    # ── Metadata ───────────────────────────────────────────────────────

    @property
    def plugin_id(self) -> str:
        return "git_manager"

    @property
    def plugin_name(self) -> str:
        return _("Git Manager")

    @property
    def plugin_icon(self) -> str:
        return "document-save-symbolic"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def plugin_description(self) -> str:
        return _("Manage a Git repository in the server folder")

    # ── Lifecycle ──────────────────────────────────────────────────────

    def activate(self, parent_window, console_manager):
        super().activate(parent_window, console_manager)
        self._git_available = self._check_git_available()

    # ── UI ─────────────────────────────────────────────────────────────

    def create_page(self) -> Gtk.Widget:
        self._page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._page.set_margin_start(12)
        self._page.set_margin_end(12)
        self._page.set_margin_top(12)
        self._page.set_margin_bottom(12)

        # Title
        title = Gtk.Label()
        title.set_markup(_("<b>Git Manager</b>"))
        title.set_halign(Gtk.Align.START)
        title.set_margin_bottom(12)
        self._page.pack_start(title, False, False, 0)

        # ── Status label (shown when no server selected) ──────────────
        self._no_server_label = Gtk.Label()
        self._no_server_label.set_markup(
            "<i>" + _("Select a server to manage its Git repository.") + "</i>"
        )
        self._no_server_label.set_valign(Gtk.Align.CENTER)
        self._no_server_label.set_vexpand(True)
        self._page.pack_start(self._no_server_label, True, True, 0)

        # ── Main content (scrollable) ─────────────────────────────────
        self._content_scroll = Gtk.ScrolledWindow()
        self._content_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self._content_scroll.add(self._content_box)
        self._page.pack_start(self._content_scroll, True, True, 0)

        # Refresh when page becomes visible
        self._page.connect("map", self._on_page_mapped)

        # ─ Status section ─────────────────────────────────────────────
        status_frame = Gtk.Frame(label=_("Repository Status"))
        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        status_box.set_margin_start(8)
        status_box.set_margin_end(8)
        status_box.set_margin_top(8)
        status_box.set_margin_bottom(8)
        status_frame.add(status_box)

        # Branch + status label
        self._status_label = Gtk.Label(label="")
        self._status_label.set_halign(Gtk.Align.START)
        self._status_label.set_line_wrap(True)
        self._status_label.set_selectable(True)
        status_box.pack_start(self._status_label, False, False, 0)

        # Action buttons row
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._init_btn = Gtk.Button(label=_("Init Repo"))
        self._init_btn.set_tooltip_text(_("Initialize a new Git repository"))
        self._init_btn.connect("clicked", self._on_init_repo)
        btn_box.pack_start(self._init_btn, False, False, 0)

        self._refresh_btn = Gtk.Button(label=_("Refresh"))
        self._refresh_btn.set_tooltip_text(_("Refresh repository status"))
        self._refresh_btn.connect("clicked", self._on_refresh)
        btn_box.pack_start(self._refresh_btn, False, False, 0)

        status_box.pack_start(btn_box, False, False, 0)
        self._content_box.pack_start(status_frame, False, False, 0)

        # ─ Commit section ─────────────────────────────────────────────
        commit_frame = Gtk.Frame(label=_("Commit"))
        commit_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        commit_box.set_margin_start(8)
        commit_box.set_margin_end(8)
        commit_box.set_margin_top(8)
        commit_box.set_margin_bottom(8)
        commit_frame.add(commit_box)

        # Changed files list
        changed_label = Gtk.Label(label=_("Changed files:"))
        changed_label.set_halign(Gtk.Align.START)
        commit_box.pack_start(changed_label, False, False, 0)

        scrolled_changes = Gtk.ScrolledWindow()
        scrolled_changes.set_min_content_height(120)
        scrolled_changes.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # ListStore: selected (bool), status (str), filename (str)
        self._changes_store = Gtk.ListStore(bool, str, str)
        self._changes_tree = Gtk.TreeView(model=self._changes_store)

        toggle_renderer = Gtk.CellRendererToggle()
        toggle_renderer.connect("toggled", self._on_file_toggled)
        col_check = Gtk.TreeViewColumn("", toggle_renderer, active=0)
        self._changes_tree.append_column(col_check)

        col_status = Gtk.TreeViewColumn(_("Status"), Gtk.CellRendererText(), text=1)
        col_status.set_min_width(80)
        self._changes_tree.append_column(col_status)

        col_file = Gtk.TreeViewColumn(_("File"), Gtk.CellRendererText(), text=2)
        col_file.set_expand(True)
        self._changes_tree.append_column(col_file)

        scrolled_changes.add(self._changes_tree)
        commit_box.pack_start(scrolled_changes, True, True, 0)

        # Select all / deselect all
        select_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sel_all_btn = Gtk.Button(label=_("Select All"))
        sel_all_btn.connect("clicked", self._on_select_all)
        select_box.pack_start(sel_all_btn, False, False, 0)

        desel_all_btn = Gtk.Button(label=_("Deselect All"))
        desel_all_btn.connect("clicked", self._on_deselect_all)
        select_box.pack_start(desel_all_btn, False, False, 0)
        commit_box.pack_start(select_box, False, False, 0)

        # Commit message
        msg_label = Gtk.Label(label=_("Commit message:"))
        msg_label.set_halign(Gtk.Align.START)
        commit_box.pack_start(msg_label, False, False, 0)

        self._commit_entry = Gtk.Entry()
        self._commit_entry.set_placeholder_text(_("Describe your changes…"))
        commit_box.pack_start(self._commit_entry, False, False, 0)

        commit_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._commit_btn = Gtk.Button(label=_("Commit"))
        self._commit_btn.get_style_context().add_class("suggested-action")
        self._commit_btn.connect("clicked", self._on_commit)
        commit_btn_box.pack_start(self._commit_btn, False, False, 0)

        self._commit_push_btn = Gtk.Button(label=_("Commit & Push"))
        self._commit_push_btn.connect("clicked", self._on_commit_and_push)
        commit_btn_box.pack_start(self._commit_push_btn, False, False, 0)

        commit_box.pack_start(commit_btn_box, False, False, 0)

        self._content_box.pack_start(commit_frame, True, True, 0)

        # ─ History section ────────────────────────────────────────────
        history_frame = Gtk.Frame(label=_("History"))
        history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        history_box.set_margin_start(8)
        history_box.set_margin_end(8)
        history_box.set_margin_top(8)
        history_box.set_margin_bottom(8)
        history_frame.add(history_box)

        scrolled_log = Gtk.ScrolledWindow()
        scrolled_log.set_min_content_height(150)
        scrolled_log.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # ListStore: hash (str), date (str), author (str), message (str)
        self._log_store = Gtk.ListStore(str, str, str, str)
        self._log_tree = Gtk.TreeView(model=self._log_store)

        for i, (title, width) in enumerate([
            (_("Hash"), 90),
            (_("Date"), 140),
            (_("Author"), 120),
            (_("Message"), -1),
        ]):
            renderer = Gtk.CellRendererText()
            if i == 3:
                renderer.set_property("ellipsize", Pango.EllipsizeMode.END)
            col = Gtk.TreeViewColumn(title, renderer, text=i)
            if width > 0:
                col.set_min_width(width)
            else:
                col.set_expand(True)
            self._log_tree.append_column(col)

        scrolled_log.add(self._log_tree)
        history_box.pack_start(scrolled_log, True, True, 0)

        self._content_box.pack_start(history_frame, True, True, 0)

        # ─ Branch section ─────────────────────────────────────────────
        branch_frame = Gtk.Frame(label=_("Branches"))
        branch_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        branch_box.set_margin_start(8)
        branch_box.set_margin_end(8)
        branch_box.set_margin_top(8)
        branch_box.set_margin_bottom(8)
        branch_frame.add(branch_box)

        branch_top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self._branch_combo = Gtk.ComboBoxText()
        branch_top_box.pack_start(self._branch_combo, True, True, 0)

        switch_btn = Gtk.Button(label=_("Switch"))
        switch_btn.set_tooltip_text(_("Switch to the selected branch"))
        switch_btn.connect("clicked", self._on_switch_branch)
        branch_top_box.pack_start(switch_btn, False, False, 0)

        branch_box.pack_start(branch_top_box, False, False, 0)

        new_branch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._new_branch_entry = Gtk.Entry()
        self._new_branch_entry.set_placeholder_text(_("New branch name…"))
        new_branch_box.pack_start(self._new_branch_entry, True, True, 0)

        create_branch_btn = Gtk.Button(label=_("Create Branch"))
        create_branch_btn.connect("clicked", self._on_create_branch)
        new_branch_box.pack_start(create_branch_btn, False, False, 0)

        branch_box.pack_start(new_branch_box, False, False, 0)

        self._content_box.pack_start(branch_frame, False, False, 0)

        # ─ Remote section ─────────────────────────────────────────────
        remote_frame = Gtk.Frame(label=_("Remote"))
        remote_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        remote_box.set_margin_start(8)
        remote_box.set_margin_end(8)
        remote_box.set_margin_top(8)
        remote_box.set_margin_bottom(8)
        remote_frame.add(remote_box)

        remote_url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._remote_entry = Gtk.Entry()
        self._remote_entry.set_placeholder_text(_("Remote URL (e.g. https://github.com/…)"))
        remote_url_box.pack_start(self._remote_entry, True, True, 0)

        set_remote_btn = Gtk.Button(label=_("Set Remote"))
        set_remote_btn.connect("clicked", self._on_set_remote)
        remote_url_box.pack_start(set_remote_btn, False, False, 0)

        remote_box.pack_start(remote_url_box, False, False, 0)

        remote_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        pull_btn = Gtk.Button(label=_("Pull"))
        pull_btn.connect("clicked", self._on_pull)
        remote_btn_box.pack_start(pull_btn, False, False, 0)

        push_btn = Gtk.Button(label=_("Push"))
        push_btn.connect("clicked", self._on_push)
        remote_btn_box.pack_start(push_btn, False, False, 0)

        remote_box.pack_start(remote_btn_box, False, False, 0)

        self._content_box.pack_start(remote_frame, False, False, 0)

        # ─ .gitignore section ─────────────────────────────────────────
        gitignore_frame = Gtk.Frame(label=".gitignore")
        gitignore_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        gitignore_box.set_margin_start(8)
        gitignore_box.set_margin_end(8)
        gitignore_box.set_margin_top(8)
        gitignore_box.set_margin_bottom(8)
        gitignore_frame.add(gitignore_box)

        gitignore_info = Gtk.Label(
            label=_("Edit the .gitignore file to exclude files from version control.")
        )
        gitignore_info.set_halign(Gtk.Align.START)
        gitignore_info.set_line_wrap(True)
        gitignore_box.pack_start(gitignore_info, False, False, 0)

        scrolled_ignore = Gtk.ScrolledWindow()
        scrolled_ignore.set_min_content_height(100)
        scrolled_ignore.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self._gitignore_buffer = Gtk.TextBuffer()
        gitignore_view = Gtk.TextView(buffer=self._gitignore_buffer)
        gitignore_view.set_monospace(True)
        scrolled_ignore.add(gitignore_view)
        gitignore_box.pack_start(scrolled_ignore, True, True, 0)

        ignore_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        save_ignore_btn = Gtk.Button(label=_("Save .gitignore"))
        save_ignore_btn.get_style_context().add_class("suggested-action")
        save_ignore_btn.connect("clicked", self._on_save_gitignore)
        ignore_btn_box.pack_start(save_ignore_btn, False, False, 0)

        default_ignore_btn = Gtk.Button(label=_("Load Default"))
        default_ignore_btn.set_tooltip_text(_("Load a default .gitignore for Minecraft servers"))
        default_ignore_btn.connect("clicked", self._on_load_default_gitignore)
        ignore_btn_box.pack_start(default_ignore_btn, False, False, 0)

        gitignore_box.pack_start(ignore_btn_box, False, False, 0)

        self._content_box.pack_start(gitignore_frame, False, False, 0)

        return self._page

    # ── Server selection ───────────────────────────────────────────────

    def select_server(self, server):
        super().select_server(server)
        self._update_visibility()

    def _on_page_mapped(self, widget):
        """Called when the page becomes visible – re-check server state."""
        self._update_visibility()

    def _update_visibility(self):
        """Show content or placeholder depending on server selection."""
        if self._selected_server and self._selected_server.path:
            self._no_server_label.hide()
            self._content_scroll.show_all()
            self._refresh_all()
        else:
            self._no_server_label.show()
            self._content_scroll.hide()

    # ── Internal helpers ───────────────────────────────────────────────

    def _server_path(self) -> str:
        if self._selected_server:
            return self._selected_server.path
        return ""

    def _is_git_repo(self) -> bool:
        return os.path.isdir(os.path.join(self._server_path(), ".git"))

    @staticmethod
    def _check_git_available() -> bool:
        try:
            subprocess.run(
                ["git", "--version"],
                capture_output=True, check=True, timeout=5
            )
            return True
        except Exception:
            return False

    def _run_git(self, *args, **kwargs) -> subprocess.CompletedProcess:
        """Run a git command in the server directory."""
        return subprocess.run(
            ["git"] + list(args),
            cwd=self._server_path(),
            capture_output=True,
            text=True,
            timeout=kwargs.get("timeout", 30),
        )

    def _run_git_async(self, args, callback=None):
        """Run a git command asynchronously and call callback(result) on the main thread."""
        def _worker():
            try:
                result = self._run_git(*args)
                if callback:
                    GLib.idle_add(callback, result)
            except Exception as e:
                if callback:
                    GLib.idle_add(callback, e)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    # ── Refresh ────────────────────────────────────────────────────────

    def _refresh_all(self):
        if not self._server_path():
            return

        is_repo = self._is_git_repo()
        self._init_btn.set_visible(not is_repo)
        self._init_btn.set_no_show_all(is_repo)

        if is_repo:
            self._refresh_status()
            self._refresh_changes()
            self._refresh_log()
            self._refresh_branches()
            self._load_gitignore()
            self._refresh_remote()
        else:
            self._status_label.set_markup(
                _("<i>No Git repository found. Click <b>Init Repo</b> to create one.</i>")
            )
            self._changes_store.clear()
            self._log_store.clear()
            self._branch_combo.remove_all()

    def _refresh_status(self):
        try:
            branch_result = self._run_git("branch", "--show-current")
            branch = branch_result.stdout.strip() or "HEAD"

            status_result = self._run_git("status", "--short")
            n_changes = len([l for l in status_result.stdout.splitlines() if l.strip()])

            self._status_label.set_markup(
                _("<b>Branch:</b> {branch}  •  <b>Changes:</b> {n}").format(
                    branch=branch, n=n_changes
                )
            )
        except Exception as e:
            self._status_label.set_text(f"Error: {e}")

    def _refresh_changes(self):
        self._changes_store.clear()
        try:
            result = self._run_git("status", "--porcelain")
            for line in result.stdout.splitlines():
                if len(line) < 4:
                    continue
                status_code = line[:2].strip()
                filename = line[3:]
                # Map status codes
                status_map = {
                    "M": _("Modified"),
                    "A": _("Added"),
                    "D": _("Deleted"),
                    "R": _("Renamed"),
                    "C": _("Copied"),
                    "??": _("Untracked"),
                    "UU": _("Conflict"),
                    "MM": _("Modified"),
                    "AM": _("Added+Mod"),
                }
                status_text = status_map.get(status_code, status_code)
                self._changes_store.append([True, status_text, filename])
        except Exception as e:
            self.log(f"[Git] Error refreshing changes: {e}\n")

    def _refresh_log(self):
        self._log_store.clear()
        try:
            result = self._run_git(
                "log", "--oneline", "--format=%h|%ai|%an|%s", "-30"
            )
            for line in result.stdout.splitlines():
                parts = line.split("|", 3)
                if len(parts) == 4:
                    self._log_store.append(parts)
        except Exception:
            pass

    def _refresh_branches(self):
        self._branch_combo.remove_all()
        try:
            result = self._run_git("branch", "--list")
            current = ""
            branches = []
            for line in result.stdout.splitlines():
                name = line.strip().lstrip("* ")
                if line.strip().startswith("*"):
                    current = name
                branches.append(name)

            for b in branches:
                self._branch_combo.append_text(b)

            # Select current branch
            if current:
                for i, b in enumerate(branches):
                    if b == current:
                        self._branch_combo.set_active(i)
                        break
        except Exception:
            pass

    def _refresh_remote(self):
        try:
            result = self._run_git("remote", "get-url", "origin")
            url = result.stdout.strip()
            self._remote_entry.set_text(url)
        except Exception:
            self._remote_entry.set_text("")

    def _load_gitignore(self):
        gitignore_path = os.path.join(self._server_path(), ".gitignore")
        if os.path.isfile(gitignore_path):
            try:
                with open(gitignore_path, "r") as f:
                    self._gitignore_buffer.set_text(f.read())
            except Exception:
                self._gitignore_buffer.set_text("")
        else:
            self._gitignore_buffer.set_text("")

    # ── Event handlers ─────────────────────────────────────────────────

    def _on_refresh(self, widget):
        self._refresh_all()

    def _on_init_repo(self, widget):
        if not self._server_path():
            return

        def _done(result):
            if isinstance(result, Exception):
                self.log(f"[Git] Error initializing repo: {result}\n")
                return
            if result.returncode == 0:
                self.log(f"[Git] Repository initialized at {self._server_path()}\n")
                # Write default .gitignore
                self._write_default_gitignore()
                # Initial commit
                self._run_git("add", ".gitignore")
                self._run_git("commit", "-m", "Initial commit – add .gitignore")
                self._refresh_all()
            else:
                self.log(f"[Git] git init error: {result.stderr}\n")

        self._run_git_async(["init"], _done)

    def _on_file_toggled(self, renderer, path):
        self._changes_store[path][0] = not self._changes_store[path][0]

    def _on_select_all(self, widget):
        for row in self._changes_store:
            row[0] = True

    def _on_deselect_all(self, widget):
        for row in self._changes_store:
            row[0] = False

    def _get_selected_files(self):
        return [row[2] for row in self._changes_store if row[0]]

    def _on_commit(self, widget):
        self._do_commit(push=False)

    def _on_commit_and_push(self, widget):
        self._do_commit(push=True)

    def _do_commit(self, push=False):
        message = self._commit_entry.get_text().strip()
        if not message:
            self._show_message_dialog(
                _("Commit Error"),
                _("Please enter a commit message."),
                Gtk.MessageType.WARNING,
            )
            return

        files = self._get_selected_files()
        if not files:
            self._show_message_dialog(
                _("Commit Error"),
                _("No files selected for commit."),
                Gtk.MessageType.WARNING,
            )
            return

        def _worker():
            try:
                # Stage selected files
                for f in files:
                    self._run_git("add", "--", f)

                result = self._run_git("commit", "-m", message)
                if result.returncode == 0:
                    GLib.idle_add(self.log, f"[Git] Committed: {message}\n")
                    if push:
                        push_result = self._run_git("push", timeout=60)
                        if push_result.returncode == 0:
                            GLib.idle_add(self.log, "[Git] Pushed successfully.\n")
                        else:
                            GLib.idle_add(
                                self.log,
                                f"[Git] Push error: {push_result.stderr}\n",
                            )
                else:
                    GLib.idle_add(
                        self.log, f"[Git] Commit error: {result.stderr}\n"
                    )
            except Exception as e:
                GLib.idle_add(self.log, f"[Git] Error: {e}\n")
            finally:
                GLib.idle_add(self._post_commit_refresh)

        threading.Thread(target=_worker, daemon=True).start()

    def _post_commit_refresh(self):
        self._commit_entry.set_text("")
        self._refresh_all()

    def _on_switch_branch(self, widget):
        branch = self._branch_combo.get_active_text()
        if not branch:
            return

        def _done(result):
            if isinstance(result, Exception):
                self.log(f"[Git] Error switching branch: {result}\n")
                return
            if result.returncode == 0:
                self.log(f"[Git] Switched to branch: {branch}\n")
                self._refresh_all()
            else:
                self.log(f"[Git] {result.stderr}\n")

        self._run_git_async(["checkout", branch], _done)

    def _on_create_branch(self, widget):
        name = self._new_branch_entry.get_text().strip()
        if not name:
            return

        def _done(result):
            if isinstance(result, Exception):
                self.log(f"[Git] Error creating branch: {result}\n")
                return
            if result.returncode == 0:
                self.log(f"[Git] Created and switched to branch: {name}\n")
                self._new_branch_entry.set_text("")
                self._refresh_all()
            else:
                self.log(f"[Git] {result.stderr}\n")

        self._run_git_async(["checkout", "-b", name], _done)

    def _on_set_remote(self, widget):
        url = self._remote_entry.get_text().strip()
        if not url:
            return

        try:
            # Check if origin already exists
            check = self._run_git("remote", "get-url", "origin")
            if check.returncode == 0:
                self._run_git("remote", "set-url", "origin", url)
            else:
                self._run_git("remote", "add", "origin", url)
            self.log(f"[Git] Remote origin set to: {url}\n")
        except Exception as e:
            self.log(f"[Git] Error setting remote: {e}\n")

    def _on_pull(self, widget):
        self.log("[Git] Pulling…\n")

        def _done(result):
            if isinstance(result, Exception):
                self.log(f"[Git] Pull error: {result}\n")
                return
            if result.returncode == 0:
                self.log(f"[Git] Pull complete.\n{result.stdout}\n")
                self._refresh_all()
            else:
                self.log(f"[Git] Pull error: {result.stderr}\n")

        self._run_git_async(["pull"], _done)

    def _on_push(self, widget):
        self.log("[Git] Pushing…\n")

        def _done(result):
            if isinstance(result, Exception):
                self.log(f"[Git] Push error: {result}\n")
                return
            if result.returncode == 0:
                self.log(f"[Git] Push complete.\n")
                self._refresh_all()
            else:
                self.log(f"[Git] Push error: {result.stderr}\n")

        self._run_git_async(["push"], _done)

    def _on_save_gitignore(self, widget):
        gitignore_path = os.path.join(self._server_path(), ".gitignore")
        start = self._gitignore_buffer.get_start_iter()
        end = self._gitignore_buffer.get_end_iter()
        content = self._gitignore_buffer.get_text(start, end, True)
        try:
            with open(gitignore_path, "w") as f:
                f.write(content)
            self.log("[Git] .gitignore saved.\n")
        except Exception as e:
            self.log(f"[Git] Error saving .gitignore: {e}\n")

    def _on_load_default_gitignore(self, widget):
        self._gitignore_buffer.set_text(self._default_gitignore_content())

    # ── Utilities ──────────────────────────────────────────────────────

    def _write_default_gitignore(self):
        gitignore_path = os.path.join(self._server_path(), ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, "w") as f:
                f.write(self._default_gitignore_content())

    @staticmethod
    def _default_gitignore_content() -> str:
        return """\
# Minecraft Server – default .gitignore

# Server jar files (large binaries)
*.jar

# World data (usually too large for git)
world/
world_nether/
world_the_end/

# Logs
logs/
*.log
*.log.gz

# Crash reports
crash-reports/

# Cache / temp
cache/
*.tmp
*.bak

# OS files
.DS_Store
Thumbs.db

# Java
*.class
hs_err_pid*
"""

    def _show_message_dialog(self, title, message, msg_type=Gtk.MessageType.INFO):
        dialog = Gtk.MessageDialog(
            transient_for=self._parent_window,
            flags=Gtk.DialogFlags.MODAL,
            type=msg_type,
            buttons=Gtk.ButtonsType.OK,
            text=title,
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
