"""
Player Management Page for the Minecraft Server Manager
Provides UI to manage online players, whitelist, operators, and banned players.
"""
import gi
import gettext
from typing import Optional

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

_ = gettext.gettext

from models.server import MinecraftServer


class PlayerManagementPage:
    """Handles player management UI and events"""

    def __init__(self, parent_window, console_manager, player_controller):
        self.parent_window = parent_window
        self.console_manager = console_manager
        self.player_controller = player_controller
        self.selected_server: Optional[MinecraftServer] = None

    def create_page(self):
        """Create the player management page"""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_margin_left(12)
        page.set_margin_right(12)
        page.set_margin_top(12)
        page.set_margin_bottom(12)

        title_label = Gtk.Label()
        title_label.set_markup(_("<b>Player Management</b>"))
        title_label.set_halign(Gtk.Align.START)
        title_label.set_margin_bottom(12)
        page.pack_start(title_label, False, False, 0)

        self.server_label = Gtk.Label(label=_("Select a server to manage players."))
        self.server_label.set_halign(Gtk.Align.START)
        page.pack_start(self.server_label, False, False, 0)

        self._setup_online_players(page)
        self._setup_whitelist(page)
        self._setup_operators(page)
        self._setup_banned(page)

        return page

    def _setup_online_players(self, container):
        frame = Gtk.Frame(label=_("Online Players"))
        container.pack_start(frame, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.add(vbox)

        self.online_store = Gtk.ListStore(str)
        self.online_view = Gtk.TreeView(model=self.online_store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Name"), renderer, text=0)
        self.online_view.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.add(self.online_view)
        vbox.pack_start(scrolled, True, True, 0)

    def _setup_whitelist(self, container):
        frame = Gtk.Frame(label=_("Whitelist"))
        container.pack_start(frame, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.add(vbox)

        self.whitelist_store = Gtk.ListStore(str)
        self.whitelist_view = Gtk.TreeView(model=self.whitelist_store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Name"), renderer, text=0)
        self.whitelist_view.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.add(self.whitelist_view)
        vbox.pack_start(scrolled, True, True, 0)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        add_button = Gtk.Button(label=_("Add"))
        add_button.connect("clicked", self._on_add_whitelist)
        remove_button = Gtk.Button(label=_("Remove"))
        remove_button.connect("clicked", self._on_remove_whitelist)
        button_box.pack_start(add_button, False, False, 0)
        button_box.pack_start(remove_button, False, False, 0)
        vbox.pack_start(button_box, False, False, 0)

    def _setup_operators(self, container):
        frame = Gtk.Frame(label=_("Operators"))
        container.pack_start(frame, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.add(vbox)

        self.ops_store = Gtk.ListStore(str)
        self.ops_view = Gtk.TreeView(model=self.ops_store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Name"), renderer, text=0)
        self.ops_view.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.add(self.ops_view)
        vbox.pack_start(scrolled, True, True, 0)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        add_button = Gtk.Button(label=_("Add"))
        add_button.connect("clicked", self._on_add_operator)
        remove_button = Gtk.Button(label=_("Remove"))
        remove_button.connect("clicked", self._on_remove_operator)
        button_box.pack_start(add_button, False, False, 0)
        button_box.pack_start(remove_button, False, False, 0)
        vbox.pack_start(button_box, False, False, 0)

    def _setup_banned(self, container):
        frame = Gtk.Frame(label=_("Banned Players"))
        container.pack_start(frame, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.add(vbox)

        self.banned_store = Gtk.ListStore(str)
        self.banned_view = Gtk.TreeView(model=self.banned_store)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Name"), renderer, text=0)
        self.banned_view.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.add(self.banned_view)
        vbox.pack_start(scrolled, True, True, 0)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        add_button = Gtk.Button(label=_("Add"))
        add_button.connect("clicked", self._on_add_banned)
        remove_button = Gtk.Button(label=_("Remove"))
        remove_button.connect("clicked", self._on_remove_banned)
        button_box.pack_start(add_button, False, False, 0)
        button_box.pack_start(remove_button, False, False, 0)
        vbox.pack_start(button_box, False, False, 0)

    def _show_add_dialog(self, title: str) -> Optional[str]:
        dialog = Gtk.Dialog(title=title, parent=self.parent_window, flags=0)

        cancel_button = Gtk.Button(label=_("Cancel"))
        cancel_button.set_image(Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.BUTTON))
        cancel_button.set_always_show_image(True)
        cancel_button.connect("clicked", lambda btn: dialog.response(Gtk.ResponseType.CANCEL))
        dialog.add_action_widget(cancel_button, Gtk.ResponseType.CANCEL)

        ok_button = Gtk.Button(label=_("OK"))
        ok_button.set_image(Gtk.Image.new_from_icon_name("dialog-ok", Gtk.IconSize.BUTTON))
        ok_button.set_always_show_image(True)
        ok_button.connect("clicked", lambda btn: dialog.response(Gtk.ResponseType.OK))
        dialog.add_action_widget(ok_button, Gtk.ResponseType.OK)
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        box = dialog.get_content_area()
        box.add(entry)
        entry.show()
        response = dialog.run()
        text = entry.get_text().strip()
        dialog.destroy()
        if response == Gtk.ResponseType.OK and text:
            return text
        return None

    def _on_add_whitelist(self, widget):
        name = self._show_add_dialog(_("Add to whitelist"))
        if name and self.player_controller.add_to_whitelist(name):
            self.console_manager.log_to_console(f"{name} added to whitelist\n")
        self._refresh_whitelist()

    def _on_remove_whitelist(self, widget):
        selection = self.whitelist_view.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            name = model[iter_][0]
            if self.player_controller.remove_from_whitelist(name):
                self.console_manager.log_to_console(f"{name} removed from whitelist\n")
        self._refresh_whitelist()

    def _on_add_operator(self, widget):
        name = self._show_add_dialog(_("Add operator"))
        if name and self.player_controller.add_operator(name):
            self.console_manager.log_to_console(f"{name} added as operator\n")
        self._refresh_ops()

    def _on_remove_operator(self, widget):
        selection = self.ops_view.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            name = model[iter_][0]
            if self.player_controller.remove_operator(name):
                self.console_manager.log_to_console(f"{name} removed from operators\n")
        self._refresh_ops()

    def _on_add_banned(self, widget):
        name = self._show_add_dialog(_("Ban player"))
        if name and self.player_controller.add_banned_player(name):
            self.console_manager.log_to_console(f"{name} banned\n")
        self._refresh_banned()

    def _on_remove_banned(self, widget):
        selection = self.banned_view.get_selection()
        model, iter_ = selection.get_selected()
        if iter_:
            name = model[iter_][0]
            if self.player_controller.remove_banned_player(name):
                self.console_manager.log_to_console(f"{name} unbanned\n")
        self._refresh_banned()

    def select_server(self, server: MinecraftServer):
        """Select a server to manage players"""
        self.selected_server = server
        self.player_controller.set_server(server)
        if server:
            self.server_label.set_text(_("Managing players for: {name}").format(name=server.name))
        else:
            self.server_label.set_text(_("Select a server to manage players."))
        self.refresh_lists()

    def refresh_lists(self):
        self._refresh_online()
        self._refresh_whitelist()
        self._refresh_ops()
        self._refresh_banned()

    def _refresh_online(self):
        self.online_store.clear()
        for name in self.player_controller.get_online_players():
            self.online_store.append([name])

    def _refresh_whitelist(self):
        self.whitelist_store.clear()
        if not self.selected_server:
            return
        for name in self.player_controller.get_whitelist():
            self.whitelist_store.append([name])

    def _refresh_ops(self):
        self.ops_store.clear()
        if not self.selected_server:
            return
        for name in self.player_controller.get_operators():
            self.ops_store.append([name])

    def _refresh_banned(self):
        self.banned_store.clear()
        if not self.selected_server:
            return
        for name in self.player_controller.get_banned_players():
            self.banned_store.append([name])
