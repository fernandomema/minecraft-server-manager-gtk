"""
Plugin Management Page for the Minecraft Server Manager
Contains all UI and logic related to plugin management
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from models.server import MinecraftServer
from models.plugin import Plugin


class PluginManagementPage:
    """Handles plugin management UI and events"""
    
    def __init__(self, parent_window, plugin_controller, console_manager):
        self.parent_window = parent_window
        self.plugin_controller = plugin_controller
        self.console_manager = console_manager
        self.selected_server = None
        
        # UI Components
        self.plugin_server_label = None
        self.local_plugin_store = None
        self.local_plugin_view = None
        self.online_search_store = None
        self.online_search_view = None
        self.search_entry = None

    def create_page(self):
        """Crea la página del gestor de plugins"""
        plugin_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        plugin_page.set_margin_left(12)
        plugin_page.set_margin_right(12)
        plugin_page.set_margin_top(12)
        plugin_page.set_margin_bottom(12)

        # Título de la página
        title_label = Gtk.Label()
        title_label.set_markup("<b>Plugin Manager</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_margin_bottom(12)
        plugin_page.pack_start(title_label, False, False, 0)

        # Etiqueta de información del servidor
        self.plugin_server_label = Gtk.Label(label="Select a server to manage plugins.")
        plugin_page.pack_start(self.plugin_server_label, False, False, 0)

        # Sección de plugins locales
        self._setup_local_plugins_section(plugin_page)
        
        # Sección de búsqueda online
        self._setup_online_search_section(plugin_page)
        
        return plugin_page

    def _setup_local_plugins_section(self, container):
        """Configura la sección de plugins locales"""
        frame = Gtk.Frame(label="Local Plugins/Mods")
        container.pack_start(frame, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.add(vbox)

        # Lista de plugins locales
        self.local_plugin_store = Gtk.ListStore(str, str)  # name, path
        self.local_plugin_view = Gtk.TreeView(model=self.local_plugin_store)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Plugin/Mod Name", renderer, text=0)
        self.local_plugin_view.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.add(self.local_plugin_view)
        vbox.pack_start(scrolled, True, True, 0)

        # Botones de plugins locales
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_start(hbox, False, False, 0)

        add_button = Gtk.Button(label="Add Local Plugin")
        add_button.connect("clicked", self._on_add_local_plugin_clicked)
        hbox.pack_start(add_button, False, False, 0)

        remove_button = Gtk.Button(label="Remove Selected")
        remove_button.connect("clicked", self._on_remove_local_plugin_clicked)
        hbox.pack_start(remove_button, False, False, 0)

    def _setup_online_search_section(self, container):
        """Configura la sección de búsqueda online"""
        frame = Gtk.Frame(label="Online Search")
        container.pack_start(frame, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.add(vbox)

        # Barra de búsqueda
        search_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_start(search_hbox, False, False, 0)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search plugins/mods...")
        search_hbox.pack_start(self.search_entry, True, True, 0)

        search_button = Gtk.Button(label="Search")
        search_button.connect("clicked", self._on_search_online_clicked)
        search_hbox.pack_start(search_button, False, False, 0)

        # Lista de resultados
        self.online_search_store = Gtk.ListStore(str, str, str)  # name, source, version
        self.online_search_view = Gtk.TreeView(model=self.online_search_store)
        
        for i, title in enumerate(["Name", "Source", "Version"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.online_search_view.append_column(column)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_hexpand(True)
        scrolled.set_vexpand(True)
        scrolled.add(self.online_search_view)
        vbox.pack_start(scrolled, True, True, 0)

        # Botones de búsqueda online
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_start(hbox, False, False, 0)

        download_button = Gtk.Button(label="Download Selected")
        download_button.connect("clicked", self._on_download_online_plugin_clicked)
        hbox.pack_start(download_button, False, False, 0)

        update_button = Gtk.Button(label="Update Selected")
        update_button.connect("clicked", self._on_update_online_plugin_clicked)
        hbox.pack_start(update_button, False, False, 0)

    # Event Handlers - Plugin Management
    def _on_add_local_plugin_clicked(self, widget):
        """Maneja el clic en añadir plugin local"""
        if not self.selected_server:
            self.console_manager.log_to_console("Please select a server first.\n")
            return

        dialog = Gtk.FileChooserDialog(
            title="Select Plugin JAR File",
            parent=self.parent_window,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK
            )
        )

        # Filtro para archivos JAR
        filter_jar = Gtk.FileFilter()
        filter_jar.set_name("JAR files")
        filter_jar.add_pattern("*.jar")
        dialog.add_filter(filter_jar)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            source_path = dialog.get_filename()
            if self.plugin_controller.add_local_plugin(source_path, self.selected_server.path):
                self.plugin_controller.refresh_local_plugins(self.selected_server.path)

        dialog.destroy()

    def _on_remove_local_plugin_clicked(self, widget):
        """Maneja el clic en eliminar plugin local"""
        selection = self.local_plugin_view.get_selection()
        model, treeiter = selection.get_selected()
        
        if not treeiter:
            self.console_manager.log_to_console("Please select a plugin to remove.\n")
            return

        plugin_name = model[treeiter][0]
        plugin_path = model[treeiter][1]
        
        plugin = Plugin(plugin_name, "Local", file_path=plugin_path)
        if self.plugin_controller.remove_local_plugin(plugin):
            self.plugin_controller.refresh_local_plugins(self.selected_server.path)

    def _on_search_online_clicked(self, widget):
        """Maneja el clic en buscar online"""
        query = self.search_entry.get_text()
        if not query:
            self.console_manager.log_to_console("Please enter a search query.\n")
            return

        self.online_search_store.clear()
        self.plugin_controller.search_modrinth_plugins(query, self._on_search_results)

    def _on_download_online_plugin_clicked(self, widget):
        """Maneja el clic en descargar plugin online"""
        self.console_manager.log_to_console("Download Online Plugin functionality not yet implemented.\n")

    def _on_update_online_plugin_clicked(self, widget):
        """Maneja el clic en actualizar plugin online"""
        self.console_manager.log_to_console("Update Online Plugin functionality not yet implemented.\n")

    def select_server(self, server: MinecraftServer):
        """Selecciona un servidor para gestionar plugins"""
        self.selected_server = server
        self.update_plugin_info(server)
        if server:
            self.plugin_controller.refresh_local_plugins(server.path)

    def update_plugin_info(self, server: MinecraftServer):
        """Actualiza la información de plugins"""
        if server:
            self.plugin_server_label.set_text(f"Managing plugins for: {server.name}")
        else:
            self.plugin_server_label.set_text("Select a server to manage plugins.")

    def on_plugins_updated(self, plugins):
        """Callback cuando se actualizan los plugins"""
        if self.local_plugin_store:
            self.local_plugin_store.clear()
            for plugin in plugins:
                self.local_plugin_store.append([plugin.name, plugin.file_path or ""])

    def _on_search_results(self, plugins):
        """Callback con resultados de búsqueda"""
        if self.online_search_store:
            self.online_search_store.clear()
            for plugin in plugins:
                self.online_search_store.append([plugin.name, plugin.source, plugin.version])
