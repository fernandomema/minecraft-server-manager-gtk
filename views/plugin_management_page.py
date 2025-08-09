"""
Plugin Management Page for the Minecraft Server Manager
Contains all UI and logic related to plugin management
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib
import urllib.request
import threading
import os
import tempfile

from models.server import MinecraftServer
from models.plugin import Plugin


class PluginManagementPage:
    """Handles plugin management UI and events"""
    
    def __init__(self, parent_window, console_manager, plugin_controller):
        self.parent_window = parent_window
        self.console_manager = console_manager
        self.plugin_controller = plugin_controller
        self.selected_server = None
        
        # Caché de iconos descargados
        self.icon_cache = {}
        self.default_plugin_icon = None
        self.default_mod_icon = None
        
        # Crear iconos por defecto
        self._create_default_icons()
        
        self.plugin_controller.set_plugins_updated_callback(self.on_plugins_updated)
    
    def _create_default_icons(self):
        """Crea iconos por defecto desde los iconos del sistema"""
        try:
            icon_theme = Gtk.IconTheme.get_default()
            # Usar iconos que existen en Adwaita
            self.default_plugin_icon = icon_theme.load_icon("application-x-addon", 24, Gtk.IconLookupFlags.GENERIC_FALLBACK)
        except:
            try:
                # Fallback: usar un icono más genérico
                icon_theme = Gtk.IconTheme.get_default()
                self.default_plugin_icon = icon_theme.load_icon("package-x-generic", 24, Gtk.IconLookupFlags.GENERIC_FALLBACK)
            except:
                # Último fallback: crear pixbuf vacío
                self.default_plugin_icon = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 24, 24)
                self.default_plugin_icon.fill(0xAAAAAAFF)  # Gris
        
        try:
            icon_theme = Gtk.IconTheme.get_default()
            # Usar iconos que existen en Adwaita para mods
            self.default_mod_icon = icon_theme.load_icon("preferences-system", 24, Gtk.IconLookupFlags.GENERIC_FALLBACK)
        except:
            try:
                # Fallback: usar un icono más genérico
                icon_theme = Gtk.IconTheme.get_default()
                self.default_mod_icon = icon_theme.load_icon("package-x-generic", 24, Gtk.IconLookupFlags.GENERIC_FALLBACK)
            except:
                # Último fallback: crear pixbuf vacío
                self.default_mod_icon = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 24, 24)
                self.default_mod_icon.fill(0x0000FFFF)  # Azul

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
        plugin_type = model[iter][0]  # Ahora el tipo está en el índice 0
        if plugin_type == "plugin":
            cell.set_property("icon-name", "application-x-addon")
        elif plugin_type == "mod":
            cell.set_property("icon-name", "preferences-system")
        else:
            cell.set_property("icon-name", "package-x-generic")

    def _render_online_icon_cell(self, column, cell, model, iter, data):
        """Renderiza el icono según el tipo de plugin/mod online, descargando desde Modrinth si está disponible"""
        plugin_type = model[iter][0]
        plugin_name = model[iter][1]
        
        # Intentar obtener la URL del icono de forma segura
        try:
            icon_url = model[iter][5]
        except (IndexError, TypeError):
            icon_url = ""
        
        # Si tenemos una URL de icono, intentar descargarlo
        if icon_url and icon_url in self.icon_cache:
            # Ya está en caché
            cell.set_property("pixbuf", self.icon_cache[icon_url])
        elif icon_url:
            # Descargar icono en un hilo separado
            self._download_icon_async(icon_url, plugin_name, cell, plugin_type)
            # Mientras tanto, usar icono por defecto
            default_icon = self.default_plugin_icon if plugin_type == "plugin" else self.default_mod_icon
            cell.set_property("pixbuf", default_icon)
        else:
            # Sin URL de icono, usar icono por defecto basado en el tipo
            default_icon = self.default_plugin_icon if plugin_type == "plugin" else self.default_mod_icon
            cell.set_property("pixbuf", default_icon)
    
    def _download_icon_async(self, icon_url, plugin_name, cell, plugin_type):
        """Descarga un icono de forma asíncrona (fallback si no se precargó)"""
        # Si ya está en proceso de descarga por precarga, simplemente usar icono por defecto por ahora
        default_icon = self.default_plugin_icon if plugin_type == "plugin" else self.default_mod_icon
        cell.set_property("pixbuf", default_icon)

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
        self.local_plugin_store = Gtk.ListStore(str, str, str, str, str)  # type, icon_name, name, install_method, path
        self.local_plugin_view = Gtk.TreeView(model=self.local_plugin_store)
        
        # Columna de icono
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn("Icon", icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self._render_icon_cell)
        icon_column.set_fixed_width(50)
        self.local_plugin_view.append_column(icon_column)
        
        # Columna de tipo
        type_renderer = Gtk.CellRendererText()
        type_column = Gtk.TreeViewColumn("Type", type_renderer, text=0)
        type_column.set_fixed_width(80)
        self.local_plugin_view.append_column(type_column)
        
        # Columna de nombre
        name_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn("Plugin/Mod Name", name_renderer, text=2)
        name_column.set_expand(True)
        self.local_plugin_view.append_column(name_column)
        
        # Columna de método de instalación
        method_renderer = Gtk.CellRendererText()
        method_column = Gtk.TreeViewColumn("Install Method", method_renderer, text=3)
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

        # Selector de tipo de contenido
        type_label = Gtk.Label(label="Search for:")
        search_hbox.pack_start(type_label, False, False, 0)

        self.search_type_combo = Gtk.ComboBoxText()
        self.search_type_combo.append("plugin", "Plugins")
        self.search_type_combo.append("mod", "Mods")
        self.search_type_combo.append("", "Both")
        self.search_type_combo.set_active(2)  # Por defecto "Both"
        self.search_type_combo.connect("changed", self._on_search_type_changed)
        search_hbox.pack_start(self.search_type_combo, False, False, 0)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search plugins/mods...")
        self.search_entry.connect("activate", self._on_search_online_clicked)  # Buscar al presionar Enter
        search_hbox.pack_start(self.search_entry, True, True, 0)

        search_button = Gtk.Button(label="Search Online")
        search_button.connect("clicked", self._on_search_online_clicked)
        search_hbox.pack_start(search_button, False, False, 0)

        # Lista de resultados con iconos y descripción
        self.online_search_store = Gtk.ListStore(str, str, str, str, str, str)  # type, name, source, version, description, icon_url
        self.online_search_view = Gtk.TreeView(model=self.online_search_store)
        
        # Columna de icono
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn("Icon", icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self._render_online_icon_cell)
        icon_column.set_fixed_width(50)
        self.online_search_view.append_column(icon_column)
        
        # Columnas de texto
        columns = [("Type", 0), ("Name", 1), ("Source", 2), ("Version", 3)]
        for title, index in columns:
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=index)
            if title == "Name":
                column.set_expand(True)  # Expandir la columna de nombre
            elif title == "Type":
                column.set_fixed_width(80)  # Ancho fijo para la columna de tipo
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
        plugin_name = model[treeiter][2]  # Nombre (ahora en índice 2)
        install_method = model[treeiter][3]  # Método de instalación (ahora en índice 3)
        plugin_path = model[treeiter][4]  # Ruta (ahora en índice 4)
        
        plugin = Plugin(plugin_name, "Local", file_path=plugin_path, install_method=install_method)
        if self.plugin_controller.remove_local_plugin(plugin, self.selected_server.path):
            self.plugin_controller.refresh_local_plugins(self.selected_server.path)

    def _on_search_online_clicked(self, widget):
        """Maneja el clic en buscar online"""
        query = self.search_entry.get_text()
        if not query:
            self.console_manager.log_to_console("Please enter a search query.\n")
            return

        # Obtener el tipo seleccionado
        search_type = self.search_type_combo.get_active_id()
        search_type_text = self.search_type_combo.get_active_text()
        
        self.console_manager.log_to_console(f"Searching for {search_type_text.lower()} with query: '{query}'\n")
        
        self.online_search_store.clear()
        self.plugin_controller.search_modrinth_plugins(query, self._on_search_results, search_type)

    def _on_search_type_changed(self, combo):
        """Maneja el cambio en el tipo de búsqueda"""
        search_type = combo.get_active_id()
        if search_type == "plugin":
            self.search_entry.set_placeholder_text("Search plugins...")
        elif search_type == "mod":
            self.search_entry.set_placeholder_text("Search mods...")
        else:
            self.search_entry.set_placeholder_text("Search plugins/mods...")

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
        plugin_name = model[treeiter][2]  # Nombre ahora en índice 2
        install_method = model[treeiter][3]  # Método ahora en índice 3
        plugin_path = model[treeiter][4]  # Ruta ahora en índice 4
        
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
        
        # Intentar obtener la descripción de forma segura
        try:
            plugin_description = model[treeiter][4]
            if not plugin_description:
                plugin_description = "No description available"
        except (IndexError, TypeError) as e:
            plugin_description = "No description available"
            self.console_manager.log_to_console(f"DEBUG: Error getting description: {e}\n")
        
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
                    plugin_type,        # Tipo (índice 0)
                    plugin_type,        # icon_name (índice 1, no se usa directamente)
                    plugin.name,        # Nombre (índice 2)
                    display_method,     # Método de instalación (índice 3)
                    plugin.file_path or ""  # Ruta (índice 4)
                ])

    def _on_search_results(self, plugins):
        """Callback con resultados de búsqueda"""
        if self.online_search_store:
            self.online_search_store.clear()
            for plugin in plugins:
                # Determinar tipo basado en categorías de Modrinth
                plugin_type = getattr(plugin, 'project_type', 'plugin')  # Default a plugin
                description = getattr(plugin, 'description', 'No description available')
                icon_url = getattr(plugin, 'icon_url', '')
                
                row_data = [
                    plugin_type, 
                    plugin.name, 
                    plugin.source, 
                    plugin.version,
                    description,
                    icon_url
                ]
                
                print(f"DEBUG: Adding row: {row_data}")
                self.online_search_store.append(row_data)
                
                # Iniciar descarga de icono inmediatamente si hay URL
                if icon_url and icon_url not in self.icon_cache:
                    self._preload_icon(icon_url, plugin.name, plugin_type)
    
    def _preload_icon(self, icon_url, plugin_name, plugin_type):
        """Precarga un icono para que esté disponible inmediatamente"""
        def download_icon():
            try:
                print(f"DEBUG: Preloading icon for {plugin_name} from {icon_url}")
                
                # Crear un directorio temporal para los iconos
                temp_dir = os.path.join(tempfile.gettempdir(), "minecraft_server_manager_icons")
                os.makedirs(temp_dir, exist_ok=True)
                
                # Crear nombre de archivo basado en la URL
                filename = os.path.join(temp_dir, f"{hash(icon_url)}.png")
                
                # Descargar el archivo
                urllib.request.urlretrieve(icon_url, filename)
                
                # Cargar como pixbuf y redimensionar
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)
                scaled_pixbuf = pixbuf.scale_simple(24, 24, GdkPixbuf.InterpType.BILINEAR)
                
                # Guardar en caché
                self.icon_cache[icon_url] = scaled_pixbuf
                
                # Forzar actualización de la vista
                GLib.idle_add(self.online_search_view.queue_draw)
                
                # Limpiar archivo temporal
                os.remove(filename)
                
            except Exception as e:
                print(f"DEBUG: Error preloading icon for {plugin_name}: {e}")
                # En caso de error, usar icono por defecto
                default_icon = self.default_plugin_icon if plugin_type == "plugin" else self.default_mod_icon
                self.icon_cache[icon_url] = default_icon
        
        # Ejecutar descarga en hilo separado
        threading.Thread(target=download_icon, daemon=True).start()
