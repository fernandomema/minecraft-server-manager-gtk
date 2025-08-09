"""
Resource Pack Management Page for the Minecraft Server Manager
"""
import gi
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

_ = gettext.gettext

from models.server import MinecraftServer


class ResourcePackPage:
    """Handles resource pack management UI and events"""

    def __init__(self, parent_window, console_manager, resource_pack_controller):
        self.parent_window = parent_window
        self.console_manager = console_manager
        self.resource_pack_controller = resource_pack_controller
        self.selected_server = None

    def create_page(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        page.set_margin_left(12)
        page.set_margin_right(12)
        page.set_margin_top(12)
        page.set_margin_bottom(12)

        title_label = Gtk.Label()
        title_label.set_markup(_("<b>Resource Pack Manager</b>"))
        title_label.set_halign(Gtk.Align.START)
        title_label.set_margin_bottom(12)
        page.pack_start(title_label, False, False, 0)

        self.server_label = Gtk.Label(label=_("Select a server to manage resource packs."))
        self.server_label.set_halign(Gtk.Align.START)
        page.pack_start(self.server_label, False, False, 0)

        self.active_pack_label = Gtk.Label(label=_("Active pack: None"))
        self.active_pack_label.set_halign(Gtk.Align.START)
        page.pack_start(self.active_pack_label, False, False, 0)

        self.pack_store = Gtk.ListStore(str, str)  # name, sha1
        self.pack_view = Gtk.TreeView(model=self.pack_store)

        name_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn(_("Pack"), name_renderer, text=0)
        name_column.set_expand(True)
        self.pack_view.append_column(name_column)

        sha1_renderer = Gtk.CellRendererText()
        sha1_column = Gtk.TreeViewColumn(_("SHA1"), sha1_renderer, text=1)
        sha1_column.set_expand(True)
        self.pack_view.append_column(sha1_column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.add(self.pack_view)
        page.pack_start(scrolled, True, True, 0)

        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        self.url_entry = Gtk.Entry()
        self.url_entry.set_placeholder_text(_("Resource pack URL"))
        controls_box.pack_start(self.url_entry, True, True, 0)

        download_button = Gtk.Button(label=_("Download"))
        download_button.connect("clicked", self.on_download_clicked)
        controls_box.pack_start(download_button, False, False, 0)

        activate_button = Gtk.Button(label=_("Activate"))
        activate_button.connect("clicked", self.on_activate_clicked)
        controls_box.pack_start(activate_button, False, False, 0)

        deactivate_button = Gtk.Button(label=_("Deactivate"))
        deactivate_button.connect("clicked", self.on_deactivate_clicked)
        controls_box.pack_start(deactivate_button, False, False, 0)

        page.pack_start(controls_box, False, False, 0)

        return page

    def select_server(self, server: MinecraftServer):
        """Selecciona un servidor para gestionar resource packs"""
        self.selected_server = server
        if server:
            self.server_label.set_text(_("Managing resource packs for: {name}").format(name=server.name))
            self.resource_pack_controller.refresh_resource_packs(server.path)
        else:
            self.server_label.set_text(_("Select a server to manage resource packs."))
            self.active_pack_label.set_text(_("Active pack: None"))
            if self.pack_store:
                self.pack_store.clear()

    def on_packs_updated(self, packs, active):
        if self.pack_store:
            self.pack_store.clear()
            for name, sha1 in packs:
                self.pack_store.append([name, sha1])
        active_url, active_sha1 = active
        if active_url:
            self.active_pack_label.set_text(_("Active pack URL: {url}").format(url=active_url))
        else:
            self.active_pack_label.set_text(_("Active pack: None"))

    def on_download_clicked(self, widget):
        if not self.selected_server:
            return
        url = self.url_entry.get_text().strip()
        if not url:
            return
        self.resource_pack_controller.download_resource_pack(url, self.selected_server)
        self.url_entry.set_text("")

    def on_activate_clicked(self, widget):
        if not self.selected_server:
            return
        selection = self.pack_view.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            filename = model[treeiter][0]
            if self.resource_pack_controller.activate_resource_pack(self.selected_server, filename):
                self.parent_window.server_controller.save_servers()

    def on_deactivate_clicked(self, widget):
        if not self.selected_server:
            return
        self.resource_pack_controller.deactivate_resource_pack(self.selected_server)
        self.parent_window.server_controller.save_servers()
