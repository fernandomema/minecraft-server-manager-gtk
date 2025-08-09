"""Port Analysis Page for the Minecraft Server Manager"""
import gi
import subprocess
import gettext
import re

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

_ = gettext.gettext


class PortAnalysisPage:
    """Provides UI to analyze listening ports for running servers."""

    def __init__(self, server_controller):
        self.liststore = None
        self.status_label = None
        self.server_controller = server_controller

    def create_page(self):
        """Creates the port analysis page."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_margin_left(12)
        page.set_margin_right(12)
        page.set_margin_top(12)
        page.set_margin_bottom(12)

        title_label = Gtk.Label()
        title_label.set_markup(_("<b>Port Analyzer</b>"))
        title_label.set_halign(Gtk.Align.START)
        title_label.set_margin_bottom(12)
        page.pack_start(title_label, False, False, 0)

        refresh_button = Gtk.Button(label=_("Refresh Ports"))
        refresh_button.connect("clicked", self._on_refresh_clicked)
        page.pack_start(refresh_button, False, False, 0)

        self.status_label = Gtk.Label()
        self.status_label.set_halign(Gtk.Align.START)
        page.pack_start(self.status_label, False, False, 0)

        self.liststore = Gtk.ListStore(str, str, str, str, str, str)
        treeview = Gtk.TreeView(model=self.liststore)
        for i, title in enumerate([_("Proto"), _("State"), _("Local"), _("Remote"), _("PID"), _("Program")]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            column.set_resizable(True)
            treeview.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.add(treeview)
        page.pack_start(scrolled, True, True, 0)

        self._refresh_ports()

        return page

    def _on_refresh_clicked(self, widget):
        self._refresh_ports()

    def _refresh_ports(self):
        """Refreshes the list of listening ports for the server process."""
        self.liststore.clear()
        self.status_label.set_text("")

        pids = [proc.pid for proc in self.server_controller.running_servers.values() if proc and proc.pid]
        if not pids:
            self.status_label.set_text(_("No servers are currently running."))
            return

        try:
            output = subprocess.check_output(["ss", "-tulpn"], stderr=subprocess.STDOUT, text=True)
            lines = [line for line in output.splitlines() if any(f"pid={pid}," in line for pid in pids)]

            seen = set()
            for line in lines:
                parts = line.split()
                if len(parts) < 6:
                    continue
                proto = parts[0]
                state = parts[1]
                local = parts[4]
                remote = parts[5]
                match = re.search(r'users:\(\("([^"]+)",pid=(\d+)', line)
                program, pid = (match.group(1), match.group(2)) if match else ("", "")
                key = (proto, local, pid)
                if key in seen:
                    continue
                seen.add(key)
                self.liststore.append([proto, state, local, remote, pid, program])

            if len(self.liststore) == 0:
                self.status_label.set_text(_("No listening ports found for running servers."))
        except Exception as e:
            self.status_label.set_text(_("Failed to retrieve ports: {error}").format(error=str(e)))

