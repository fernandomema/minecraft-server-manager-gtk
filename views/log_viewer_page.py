"""
Log Viewer Page for the Minecraft Server Manager
Lists available log files and displays their contents
"""
import gi
import os
import gettext
import gzip

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from models.server import MinecraftServer

_ = gettext.gettext


class LogViewerPage:
    """Handles log viewing UI and events"""

    def __init__(self, server_controller):
        self.server_controller = server_controller
        self.selected_server = None

        self.log_store = None
        self.log_tree = None
        self.log_textbuffer = None
        self.server_info_label = None

    def create_page(self):
        """Crea la página del visor de logs"""
        log_page = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        log_page.set_margin_left(12)
        log_page.set_margin_right(12)
        log_page.set_margin_top(12)
        log_page.set_margin_bottom(12)

        # Panel izquierdo: lista de archivos de log
        logs_frame = Gtk.Frame(label=_("Log Files"))
        logs_frame.set_size_request(250, -1)
        log_page.pack_start(logs_frame, False, False, 0)

        logs_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        logs_box.set_margin_left(6)
        logs_box.set_margin_right(6)
        logs_box.set_margin_top(6)
        logs_box.set_margin_bottom(6)
        logs_frame.add(logs_box)

        self.server_info_label = Gtk.Label()
        self.server_info_label.set_markup(_("<i>Select a server to view logs</i>"))
        self.server_info_label.set_halign(Gtk.Align.START)
        logs_box.pack_start(self.server_info_label, False, False, 0)

        scrolled_list = Gtk.ScrolledWindow()
        scrolled_list.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_list.set_vexpand(True)
        logs_box.pack_start(scrolled_list, True, True, 0)

        self.log_store = Gtk.ListStore(str, str)  # Nombre visible, ruta completa
        self.log_tree = Gtk.TreeView(model=self.log_store)
        self.log_tree.set_headers_visible(False)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("File"), renderer, text=0)
        self.log_tree.append_column(column)
        selection = self.log_tree.get_selection()
        selection.connect("changed", self._on_log_selected)
        scrolled_list.add(self.log_tree)

        # Panel derecho: contenido del log
        content_frame = Gtk.Frame(label=_("Log Content"))
        log_page.pack_start(content_frame, True, True, 0)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        content_box.set_margin_left(6)
        content_box.set_margin_right(6)
        content_box.set_margin_top(6)
        content_box.set_margin_bottom(6)
        content_frame.add(content_box)

        scrolled_text = Gtk.ScrolledWindow()
        scrolled_text.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_text.set_vexpand(True)
        content_box.pack_start(scrolled_text, True, True, 0)

        self.log_textbuffer = Gtk.TextBuffer()
        text_view = Gtk.TextView(buffer=self.log_textbuffer)
        text_view.set_editable(False)
        text_view.set_monospace(True)
        scrolled_text.add(text_view)

        return log_page

    def select_server(self, server: MinecraftServer):
        """Selecciona un servidor y carga sus logs"""
        self.selected_server = server
        if server:
            self.server_info_label.set_markup(_("<b>Server:</b> {name}").format(name=server.name))
            self._load_log_files()
        else:
            self.server_info_label.set_markup(_("<i>Select a server to view logs</i>"))
            self.log_store.clear()
            self.log_textbuffer.set_text("")

    def _load_log_files(self):
        """Carga la lista de archivos de log"""
        if not self.selected_server:
            return

        self.log_store.clear()
        log_files = self.server_controller.get_available_log_files(self.selected_server)
        for path in log_files:
            self.log_store.append([os.path.basename(path), path])

        if log_files:
            # Seleccionar el primer log por defecto
            tree_iter = self.log_store.get_iter_first()
            if tree_iter:
                self.log_tree.get_selection().select_iter(tree_iter)
                self._display_log_file(self.log_store.get_value(tree_iter, 1))

    def _on_log_selected(self, selection):
        model, treeiter = selection.get_selected()
        if treeiter:
            path = model.get_value(treeiter, 1)
            self._display_log_file(path)

    def _display_log_file(self, path: str):
        """Muestra el contenido del archivo de log en el área de texto"""
        try:
            if path.endswith('.gz'):
                with gzip.open(path, 'rt', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            else:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
        except Exception as e:
            content = _("Error reading log file: {error}").format(error=e)

        self.log_textbuffer.set_text(content)
