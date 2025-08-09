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

    def _render_icon_cell(self, column, cell, model, iter, data):
        """Renderiza el icono según el tipo de plugin/mod local"""
        icon_name = model[iter][0]
        if icon_name == "plugin":
            cell.set_property("icon-name", "application-x-addon")
        elif icon_name == "mod":
            cell.set_property("icon-name", "applications-games")
        else:
            cell.set_property("icon-name", "application-x-executable")

    def _render_online_icon_cell(self, column, cell, model, iter, data):
        """Renderiza el icono según el tipo de plugin/mod online"""
        plugin_type = model[iter][0]
        if plugin_type == "plugin":
            cell.set_property("icon-name", "application-x-addon")
        elif plugin_type == "mod":
            cell.set_property("icon-name", "applications-games")
        else:
            cell.set_property("icon-name", "package-x-generic")

    def _detect_plugin_type(self, filename: str) -> str:
        """Detecta si un archivo es un plugin o mod basado en su ubicación y nombre"""
        # Heurística simple: si está en "mods" o contiene "forge", "fabric", etc., es un mod
        if "/mods/" in filename or any(keyword in filename.lower() for keyword in ["forge", "fabric", "quilt", "mod"]):
            return "mod"
        else:
            return "plugin"

    def _setup_local_plugins_section(self, container):
        """Configura la sección de plugins locales"""
        frame = Gtk.Frame(label="Local Plugins/Mods")
        container.pack_start(frame, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.add(vbox)

        # Lista de plugins locales con iconos y método de instalación
        self.local_plugin_store = Gtk.ListStore(str, str, str, str)  # icon_name, name, install_method, path
        self.local_plugin_view = Gtk.TreeView(model=self.local_plugin_store)
        
        # Columna de icono
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn("Type", icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self._render_icon_cell)
        icon_column.set_fixed_width(50)
        self.local_plugin_view.append_column(icon_column)
        
        # Columna de nombre
        name_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn("Plugin/Mod Name", name_renderer, text=1)
        name_column.set_expand(True)
        self.local_plugin_view.append_column(name_column)
        
        # Columna de método de instalación
        method_renderer = Gtk.CellRendererText()
        method_column = Gtk.TreeViewColumn("Install Method", method_renderer, text=2)
        method_column.set_fixed_width(120)
        self.local_plugin_view.append_column(method_column)

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
        
        update_button = Gtk.Button(label="Update Selected")
        update_button.connect("clicked", self._on_update_local_plugin_clicked)
        hbox.pack_start(update_button, False, False, 0)

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
        self.search_entry.connect("activate", self._on_search_online_clicked)  # Buscar al presionar Enter
        search_hbox.pack_start(self.search_entry, True, True, 0)

        search_button = Gtk.Button(label="Search Online")
        search_button.connect("clicked", self._on_search_online_clicked)
        search_hbox.pack_start(search_button, False, False, 0)

        # Lista de resultados con iconos y descripción
        self.online_search_store = Gtk.ListStore(str, str, str, str, str)  # type, name, source, version, description
        self.online_search_view = Gtk.TreeView(model=self.online_search_store)
        
        # Columna de icono
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn("Type", icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self._render_online_icon_cell)
        self.online_search_view.append_column(icon_column)
        
        # Columnas de texto
        columns = [("Name", 1), ("Source", 2), ("Version", 3)]
        for title, index in columns:
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=index)
            if title == "Name":
                column.set_expand(True)  # Expandir la columna de nombre
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

        info_button = Gtk.Button(label="View Info")
        info_button.connect("clicked", self._on_view_plugin_info_clicked)
        hbox.pack_start(info_button, False, False, 0)

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

        plugin_type = model[treeiter][0]  # Tipo (plugin/mod)
        plugin_name = model[treeiter][1]  # Nombre
        install_method = model[treeiter][2]  # Método de instalación
        plugin_path = model[treeiter][3]  # Ruta
        
        plugin = Plugin(plugin_name, "Local", file_path=plugin_path, install_method=install_method)
        if self.plugin_controller.remove_local_plugin(plugin, self.selected_server.path):
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
        if not self.selected_server:
            self.console_manager.log_to_console("Please select a server first.\n")
            return
            
        selection = self.online_search_view.get_selection()
        model, treeiter = selection.get_selected()
        
        if not treeiter:
            self.console_manager.log_to_console("Please select a plugin to download.\n")
            return

        plugin_type = model[treeiter][0]
        plugin_name = model[treeiter][1]
        plugin_source = model[treeiter][2]
        plugin_version = model[treeiter][3]
        
        self.console_manager.log_to_console(f"Starting download of {plugin_name} from {plugin_source}...\n")
        
        # Por ahora, mostrar un mensaje indicando que se está trabajando en esta funcionalidad
        dialog = Gtk.MessageDialog(
            parent=self.parent_window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Download Functionality"
        )
        dialog.format_secondary_text(
            f"Download functionality for {plugin_name} is coming soon!\n\n"
            f"Plugin: {plugin_name}\n"
            f"Source: {plugin_source}\n"
            f"Version: {plugin_version}\n"
            f"Type: {plugin_type.title()}\n\n"
            "For now, please download manually and use 'Add Local Plugin'."
        )
        dialog.run()
        dialog.destroy()

    def _on_update_local_plugin_clicked(self, widget):
        """Maneja el clic en actualizar plugin local"""
        selection = self.local_plugin_view.get_selection()
        model, treeiter = selection.get_selected()
        
        if not treeiter:
            self.console_manager.log_to_console("Please select a plugin to update.\n")
            return

        plugin_type = model[treeiter][0]
        plugin_name = model[treeiter][1]
        install_method = model[treeiter][2]
        plugin_path = model[treeiter][3]
        
        if install_method == "Manual":
            dialog = Gtk.MessageDialog(
                parent=self.parent_window,
                flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Cannot Update Manual Plugin"
            )
            dialog.format_secondary_text(
                f"'{plugin_name}' was installed manually and cannot be updated automatically.\n\n"
                "To update this plugin:\n"
                "1. Download the new version manually\n"
                "2. Remove the old version\n"
                "3. Add the new version using 'Add Local Plugin'"
            )
            dialog.run()
            dialog.destroy()
        else:
            self.console_manager.log_to_console(f"Checking for updates for {plugin_name} from {install_method}...\n")
            # TODO: Implementar lógica de actualización automática
            dialog = Gtk.MessageDialog(
                parent=self.parent_window,
                flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Update Feature Coming Soon"
            )
            dialog.format_secondary_text(
                f"Automatic updates for plugins from {install_method} will be available in a future version.\n\n"
                f"Plugin: {plugin_name}\n"
                f"Source: {install_method}"
            )
            dialog.run()
            dialog.destroy()

    def _on_view_plugin_info_clicked(self, widget):
        """Maneja el clic en ver información del plugin"""
        selection = self.online_search_view.get_selection()
        model, treeiter = selection.get_selected()
        
        if not treeiter:
            self.console_manager.log_to_console("Please select a plugin to view info.\n")
            return

        plugin_type = model[treeiter][0]
        plugin_name = model[treeiter][1]
        plugin_source = model[treeiter][2]
        plugin_version = model[treeiter][3]
        plugin_description = model[treeiter][4] if len(model[treeiter]) > 4 else "No description available"
        
        dialog = Gtk.MessageDialog(
            parent=self.parent_window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=f"{plugin_name} - Information"
        )
        dialog.format_secondary_text(
            f"Name: {plugin_name}\n"
            f"Type: {plugin_type.title()}\n"
            f"Source: {plugin_source}\n"
            f"Version: {plugin_version}\n\n"
            f"Description:\n{plugin_description}"
        )
        dialog.run()
        dialog.destroy()

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
                plugin_type = self._detect_plugin_type(plugin.file_path or plugin.name)
                install_method = getattr(plugin, 'install_method', 'Manual')
                display_method = plugin.get_install_method_display() if hasattr(plugin, 'get_install_method_display') else install_method
                self.local_plugin_store.append([
                    plugin_type, 
                    plugin.name, 
                    display_method,
                    plugin.file_path or ""
                ])

    def _on_search_results(self, plugins):
        """Callback con resultados de búsqueda"""
        if self.online_search_store:
            self.online_search_store.clear()
            for plugin in plugins:
                # Determinar tipo basado en categorías de Modrinth
                plugin_type = getattr(plugin, 'project_type', 'plugin')  # Default a plugin
                description = getattr(plugin, 'description', 'No description available')
                self.online_search_store.append([
                    plugin_type, 
                    plugin.name, 
                    plugin.source, 
                    plugin.version,
                    description
                ])
