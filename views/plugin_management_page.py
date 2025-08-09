"""
Plugin Management Page for the Minecraft Server Manager
Contains all UI and logic related to plugin management
"""
import gi
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib
import urllib.request
import threading
import os
import tempfile

_ = gettext.gettext

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
        title_label.set_markup(_("<b>Plugin Manager</b>"))
        title_label.set_halign(Gtk.Align.START)
        title_label.set_margin_bottom(12)
        plugin_page.pack_start(title_label, False, False, 0)

        # Etiqueta de información del servidor
        self.plugin_server_label = Gtk.Label(label=_("Select a server to manage plugins."))
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
        """Renderiza el icono según el tipo de plugin/mod online, descargándolo de la fuente si está disponible"""
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
        """Descarga un icono de forma asíncrona usando urllib y actualiza la celda"""

        def download_icon():
            try:
                with urllib.request.urlopen(icon_url) as response:
                    data = response.read()

                loader = GdkPixbuf.PixbufLoader.new()
                loader.write(data)
                loader.close()
                pixbuf = loader.get_pixbuf()
                scaled_pixbuf = pixbuf.scale_simple(24, 24, GdkPixbuf.InterpType.BILINEAR)

                self.icon_cache[icon_url] = scaled_pixbuf
                GLib.idle_add(cell.set_property, "pixbuf", scaled_pixbuf)
            except Exception:
                default_icon = self.default_plugin_icon if plugin_type == "plugin" else self.default_mod_icon
                self.icon_cache[icon_url] = default_icon
                GLib.idle_add(cell.set_property, "pixbuf", default_icon)

        threading.Thread(target=download_icon, daemon=True).start()

    def _detect_plugin_type(self, filename: str) -> str:
        """Detecta si un archivo es un plugin o mod basado en su ubicación y nombre"""
        # Heurística simple: si está en "mods" o contiene "forge", "fabric", etc., es un mod
        if "/mods/" in filename or any(keyword in filename.lower() for keyword in ["forge", "fabric", "quilt", "mod"]):
            return "mod"
        else:
            return "plugin"

    def _setup_local_plugins_section(self, container):
        """Configura la sección de plugins locales"""
        frame = Gtk.Frame(label=_("Local Plugins/Mods"))
        container.pack_start(frame, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.add(vbox)

        # Lista de plugins locales con iconos, versión y método de instalación
        self.local_plugin_store = Gtk.ListStore(
            str, str, str, str, str, str
        )  # type, icon_name, name, version, install_method, path
        self.local_plugin_view = Gtk.TreeView(model=self.local_plugin_store)
        
        # Columna de icono
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn(_("Icon"), icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self._render_icon_cell)
        icon_column.set_fixed_width(50)
        self.local_plugin_view.append_column(icon_column)
        
        # Columna de tipo
        type_renderer = Gtk.CellRendererText()
        type_column = Gtk.TreeViewColumn(_("Type"), type_renderer, text=0)
        type_column.set_fixed_width(80)
        self.local_plugin_view.append_column(type_column)
        
        # Columna de nombre
        name_renderer = Gtk.CellRendererText()
        name_column = Gtk.TreeViewColumn(_("Plugin/Mod Name"), name_renderer, text=2)
        name_column.set_expand(True)
        self.local_plugin_view.append_column(name_column)

        # Columna de versión
        version_renderer = Gtk.CellRendererText()
        version_column = Gtk.TreeViewColumn(_("Version"), version_renderer, text=3)
        version_column.set_fixed_width(100)
        self.local_plugin_view.append_column(version_column)

        # Columna de método de instalación
        method_renderer = Gtk.CellRendererText()
        method_column = Gtk.TreeViewColumn(_("Install Method"), method_renderer, text=4)
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

        add_button = Gtk.Button(label=_("Add Local Plugin"))
        add_button.set_image(Gtk.Image.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON))
        add_button.set_always_show_image(True)
        add_button.connect("clicked", self._on_add_local_plugin_clicked)
        hbox.pack_start(add_button, False, False, 0)

        remove_button = Gtk.Button(label=_("Remove Selected"))
        remove_button.set_image(Gtk.Image.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON))
        remove_button.set_always_show_image(True)
        remove_button.connect("clicked", self._on_remove_local_plugin_clicked)
        hbox.pack_start(remove_button, False, False, 0)
        
        update_button = Gtk.Button(label=_("Update Selected"))
        update_button.connect("clicked", self._on_update_local_plugin_clicked)
        hbox.pack_start(update_button, False, False, 0)

    def _setup_online_search_section(self, container):
        """Configura la sección de búsqueda online"""
        frame = Gtk.Frame(label=_("Online Search"))
        container.pack_start(frame, True, True, 0)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        frame.add(vbox)

        # Barra de búsqueda
        search_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        vbox.pack_start(search_hbox, False, False, 0)

        # Selector de tipo de contenido
        type_label = Gtk.Label(label=_("Search for:"))
        search_hbox.pack_start(type_label, False, False, 0)

        self.search_type_combo = Gtk.ComboBoxText()
        self.search_type_combo.append("plugin", _("Plugins"))
        self.search_type_combo.append("mod", _("Mods"))
        self.search_type_combo.append("", _("Both"))
        self.search_type_combo.set_active(2)  # Por defecto "Both"
        self.search_type_combo.connect("changed", self._on_search_type_changed)
        search_hbox.pack_start(self.search_type_combo, False, False, 0)

        # Selector de fuente
        source_label = Gtk.Label(label=_("Source:"))
        search_hbox.pack_start(source_label, False, False, 0)

        self.source_combo = Gtk.ComboBoxText()
        self.source_combo.append("Modrinth", _("Modrinth"))
        self.source_combo.append("Spigot", _("Spigot"))
        self.source_combo.append("CurseForge", _("CurseForge"))
        self.source_combo.set_active(0)
        search_hbox.pack_start(self.source_combo, False, False, 0)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text(_("Search plugins/mods..."))
        self.search_entry.connect("activate", self._on_search_online_clicked)  # Buscar al presionar Enter
        search_hbox.pack_start(self.search_entry, True, True, 0)

        search_button = Gtk.Button(label=_("Search Online"))
        search_button.connect("clicked", self._on_search_online_clicked)
        search_hbox.pack_start(search_button, False, False, 0)

        # Lista de resultados con iconos y descripción
        self.online_search_store = Gtk.ListStore(str, str, str, str, str, str, str)  # type, name, source, version, description, icon_url, project_id
        self.online_search_view = Gtk.TreeView(model=self.online_search_store)
        
        # Columna de icono
        icon_renderer = Gtk.CellRendererPixbuf()
        icon_column = Gtk.TreeViewColumn(_("Icon"), icon_renderer)
        icon_column.set_cell_data_func(icon_renderer, self._render_online_icon_cell)
        icon_column.set_fixed_width(50)
        self.online_search_view.append_column(icon_column)
        
        # Columnas de texto
        columns = [(_("Type"), 0), (_("Name"), 1), (_("Source"), 2), (_("Version"), 3)]
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

        # Botón de descarga con spinner
        self.download_button = Gtk.Button()
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.download_spinner = Gtk.Spinner()
        self.download_spinner.set_no_show_all(True)
        self.download_label = Gtk.Label(_("Download Selected"))
        button_box.pack_start(self.download_spinner, False, False, 0)
        button_box.pack_start(self.download_label, False, False, 0)
        self.download_button.add(button_box)
        self.download_button.connect("clicked", self._on_download_online_plugin_clicked)
        hbox.pack_start(self.download_button, False, False, 0)

        info_button = Gtk.Button(label=_("View Info"))
        info_button.connect("clicked", self._on_view_plugin_info_clicked)
        hbox.pack_start(info_button, False, False, 0)

    # Event Handlers - Plugin Management
    def _on_add_local_plugin_clicked(self, widget):
        """Maneja el clic en añadir plugin local"""
        if not self.selected_server:
            self.console_manager.log_to_console("Please select a server first.\n")
            return

        dialog = Gtk.FileChooserDialog(
            title=_("Select Plugin JAR File"),
            parent=self.parent_window,
            action=Gtk.FileChooserAction.OPEN,
        )

        cancel_button = Gtk.Button(label=_("Cancel"))
        cancel_button.set_image(Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.BUTTON))
        cancel_button.set_always_show_image(True)
        cancel_button.connect("clicked", lambda btn: dialog.response(Gtk.ResponseType.CANCEL))
        dialog.add_action_widget(cancel_button, Gtk.ResponseType.CANCEL)

        open_button = Gtk.Button(label=_("Open"))
        open_button.set_image(Gtk.Image.new_from_icon_name("document-open", Gtk.IconSize.BUTTON))
        open_button.set_always_show_image(True)
        open_button.connect("clicked", lambda btn: dialog.response(Gtk.ResponseType.OK))
        dialog.add_action_widget(open_button, Gtk.ResponseType.OK)

        # Filtro para archivos JAR
        filter_jar = Gtk.FileFilter()
        filter_jar.set_name(_("JAR files"))
        filter_jar.add_pattern("*.jar")
        dialog.add_filter(filter_jar)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            source_path = dialog.get_filename()
            if self.plugin_controller.add_local_plugin(source_path, self.selected_server.path):
                self.plugin_controller.refresh_local_plugins(self.selected_server.path)
            else:
                # Mostrar error si no se pudo detectar el tipo o copiar
                self.console_manager.log_to_console(
                    "Could not add file. Ensure it is a valid plugin or mod JAR.\n"
                )

        dialog.destroy()

    def _on_remove_local_plugin_clicked(self, widget):
        """Maneja el clic en eliminar plugin local"""
        selection = self.local_plugin_view.get_selection()
        model, treeiter = selection.get_selected()
        
        if not treeiter:
            self.console_manager.log_to_console("Please select a plugin to remove.\n")
            return

        plugin_type = model[treeiter][0]  # Tipo (plugin/mod)
        plugin_name = model[treeiter][2]  # Nombre (índice 2)
        install_method = model[treeiter][4]  # Método de instalación (índice 4)
        plugin_path = model[treeiter][5]  # Ruta (índice 5)
        
        plugin = Plugin(plugin_name, "Local", file_path=plugin_path, install_method=install_method)
        if self.plugin_controller.remove_local_plugin(plugin, self.selected_server.path):
            self.plugin_controller.refresh_local_plugins(self.selected_server.path)

    def _on_search_online_clicked(self, widget):
        """Maneja el clic en buscar online"""
        query = self.search_entry.get_text()
        if not query:
            self.console_manager.log_to_console("Please enter a search query.\n")
            return

        # Obtener el tipo y la fuente seleccionados
        search_type = self.search_type_combo.get_active_id()
        search_type_text = self.search_type_combo.get_active_text()
        source = self.source_combo.get_active_id()

        self.console_manager.log_to_console(
            f"Searching {source} for {search_type_text.lower()} with query: '{query}'\n"
        )

        self.online_search_store.clear()
        if source == "Spigot":
            self.plugin_controller.search_spigot_plugins(query, self._on_search_results)
        elif source == "CurseForge":
            self.plugin_controller.search_curseforge_plugins(query, self._on_search_results, search_type)
        else:
            self.plugin_controller.search_modrinth_plugins(query, self._on_search_results, search_type)

    def _on_search_type_changed(self, combo):
        """Maneja el cambio en el tipo de búsqueda"""
        search_type = combo.get_active_id()
        if search_type == "plugin":
            self.search_entry.set_placeholder_text(_("Search plugins..."))
        elif search_type == "mod":
            self.search_entry.set_placeholder_text(_("Search mods..."))
        else:
            self.search_entry.set_placeholder_text(_("Search plugins/mods..."))

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
        
        # Obtener el project_id de forma segura
        try:
            project_id = model[treeiter][6]
        except (IndexError, TypeError):
            project_id = ""
        
        if not project_id:
            self.console_manager.log_to_console("Error: No project ID available for download.\n")
            return

        self.console_manager.log_to_console(f"Starting download of {plugin_name} from {plugin_source}...\n")

        # Mostrar spinner y desactivar el botón durante la descarga
        self.download_button.set_sensitive(False)
        self.download_label.hide()
        self.download_spinner.show()
        self.download_spinner.start()

        # Callback para manejar el resultado de la descarga
        def download_callback(success, message):
            # Restaurar el estado del botón
            self.download_spinner.stop()
            self.download_spinner.hide()
            self.download_label.show()
            self.download_button.set_sensitive(True)

            if success:
                self.console_manager.log_to_console(f"✓ {message}\n")
                # Refrescar la lista de plugins locales
                self.plugin_controller.refresh_local_plugins(self.selected_server.path)
                
                # Mostrar diálogo de éxito
                dialog = Gtk.MessageDialog(
                    parent=self.parent_window,
                    flags=Gtk.DialogFlags.MODAL,
                    message_type=Gtk.MessageType.INFO,
                    buttons=Gtk.ButtonsType.OK,
                    text="Download Successful"
                )
                dialog.format_secondary_text(f"{plugin_name} has been successfully downloaded and installed!")
                dialog.run()
                dialog.destroy()
            else:
                self.console_manager.log_to_console(f"✗ Download failed: {message}\n")
                
                # Mostrar diálogo de error
                dialog = Gtk.MessageDialog(
                    parent=self.parent_window,
                    flags=Gtk.DialogFlags.MODAL,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Download Failed"
                )
                dialog.format_secondary_text(f"Failed to download {plugin_name}:\n{message}")
                dialog.run()
                dialog.destroy()
        
        # Iniciar descarga según la fuente
        if plugin_source == "Spigot":
            self.plugin_controller.download_spigot_plugin(
                plugin_name,
                project_id,
                self.selected_server.path,
                download_callback,
            )
        elif plugin_source == "CurseForge":
            self.plugin_controller.download_curseforge_plugin(
                plugin_name,
                project_id,
                self.selected_server.path,
                download_callback,
            )
        else:
            self.plugin_controller.download_modrinth_plugin(
                plugin_name,
                project_id,
                self.selected_server.path,
                download_callback,
            )

    def _on_update_local_plugin_clicked(self, widget):
        """Maneja el clic en actualizar plugin local"""
        selection = self.local_plugin_view.get_selection()
        model, treeiter = selection.get_selected()
        
        if not treeiter:
            self.console_manager.log_to_console("Please select a plugin to update.\n")
            return

        plugin_type = model[treeiter][0]
        plugin_name = model[treeiter][2]  # Nombre ahora en índice 2
        install_method = model[treeiter][4]  # Método ahora en índice 4
        plugin_path = model[treeiter][5]  # Ruta ahora en índice 5
        
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
            # Obtener el objeto Plugin para acceder a metadatos
            plugins = self.plugin_controller.get_local_plugins(self.selected_server.path)
            plugin_obj = next((p for p in plugins if p.name == plugin_name), None)

            if not plugin_obj or not plugin_obj.project_id:
                self.console_manager.log_to_console(f"Cannot update {plugin_name}: missing project ID.\n")
                dialog = Gtk.MessageDialog(
                    parent=self.parent_window,
                    flags=Gtk.DialogFlags.MODAL,
                    message_type=Gtk.MessageType.ERROR,
                    buttons=Gtk.ButtonsType.OK,
                    text="Update Not Available",
                )
                dialog.format_secondary_text(
                    f"'{plugin_name}' cannot be updated automatically because its project ID is unknown."
                )
                dialog.run()
                dialog.destroy()
                return

            self.console_manager.log_to_console(
                f"Checking for updates for {plugin_name} from {plugin_obj.install_method}...\n"
            )

            def update_callback(success, message):
                if success:
                    self.console_manager.log_to_console(f"✓ {message}\n")
                    self.plugin_controller.refresh_local_plugins(self.selected_server.path)
                    dialog = Gtk.MessageDialog(
                        parent=self.parent_window,
                        flags=Gtk.DialogFlags.MODAL,
                        message_type=Gtk.MessageType.INFO,
                        buttons=Gtk.ButtonsType.OK,
                        text="Update Successful",
                    )
                    dialog.format_secondary_text(
                        f"{plugin_name} has been updated successfully."
                    )
                else:
                    self.console_manager.log_to_console(f"✗ Update failed: {message}\n")
                    dialog = Gtk.MessageDialog(
                        parent=self.parent_window,
                        flags=Gtk.DialogFlags.MODAL,
                        message_type=Gtk.MessageType.ERROR,
                        buttons=Gtk.ButtonsType.OK,
                        text="Update Failed",
                    )
                    dialog.format_secondary_text(
                        f"Failed to update {plugin_name}:\n{message}"
                    )
                dialog.run()
                dialog.destroy()

            self.plugin_controller.update_plugin(plugin_obj, self.selected_server.path, update_callback)

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
            self.plugin_server_label.set_text(_("Managing plugins for: {name}").format(name=server.name))
        else:
            self.plugin_server_label.set_text(_("Select a server to manage plugins."))

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
                    plugin.version,     # Versión (índice 3)
                    display_method,     # Método de instalación (índice 4)
                    plugin.file_path or ""  # Ruta (índice 5)
                ])

    def _on_search_results(self, plugins):
        """Callback con resultados de búsqueda"""
        if self.online_search_store:
            self.online_search_store.clear()
            for plugin in plugins:
                # Determinar tipo basado en categorías de Modrinth
                plugin_type = getattr(plugin, 'project_type', 'plugin')  # Default a plugin
                plugin_type_display = plugin_type.capitalize()  # Capitalizar para mostrar (Mod, Plugin)
                description = getattr(plugin, 'description', 'No description available')
                icon_url = getattr(plugin, 'icon_url', '')
                project_id = getattr(plugin, 'project_id', '')
                
                row_data = [
                    plugin_type_display,  # Mostrar con mayúscula inicial
                    plugin.name, 
                    plugin.source, 
                    plugin.version,
                    description,
                    icon_url,
                    project_id
                ]
                
                self.online_search_store.append(row_data)
                
                # Iniciar descarga de icono inmediatamente si hay URL
                if icon_url and icon_url not in self.icon_cache:
                    self._preload_icon(icon_url, plugin.name, plugin_type)
    
    def _preload_icon(self, icon_url, plugin_name, plugin_type):
        """Precarga un icono para que esté disponible inmediatamente"""
        def download_icon():
            try:
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
                # En caso de error, usar icono por defecto
                default_icon = self.default_plugin_icon if plugin_type == "plugin" else self.default_mod_icon
                self.icon_cache[icon_url] = default_icon
        
        # Ejecutar descarga en hilo separado
        threading.Thread(target=download_icon, daemon=True).start()
