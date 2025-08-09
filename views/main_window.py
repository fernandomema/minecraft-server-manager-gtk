"""
Ventana principal de la aplicación Minecraft Server Manager
"""
import gi
import os
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from controllers.server_controller import ServerController
from controllers.download_controller import DownloadController
from controllers.plugin_controller import PluginController
from views.add_server_dialog import AddServerDialog
from views.download_server_dialog import DownloadServerDialog
from views.eula_dialog import EulaDialog
from models.server import MinecraftServer
from models.plugin import Plugin


class MinecraftServerManager(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Minecraft Server Manager")
        self.set_default_size(1000, 700)

        # Inicializar controladores
        self._init_controllers()
        
        # Variables de estado
        self.selected_server = None
        
        # Configurar interfaz
        self._setup_css()
        self._setup_ui()
        self._setup_console()
        
        # Cargar datos iniciales
        self._load_initial_data()
        
        self.connect("destroy", Gtk.main_quit)

    def _init_controllers(self):
        """Inicializa los controladores"""
        self.server_controller = ServerController()
        self.download_controller = DownloadController()
        self.plugin_controller = PluginController()
        
        # Configurar callbacks
        self.server_controller.set_console_callback(self._log_to_console)
        self.server_controller.set_server_finished_callback(self._on_server_finished)
        self.download_controller.set_download_callback(self._log_to_console)
        self.plugin_controller.set_search_callback(self._log_to_console)
        self.plugin_controller.set_plugins_updated_callback(self._on_plugins_updated)

    def _setup_css(self):
        """Configura estilos CSS personalizados"""
        css_provider = Gtk.CssProvider()
        css = """
        .sidebar {
            background-color: #f5f5f5;
            border-right: 1px solid #d4d4d4;
        }
        
        .sidebar listbox row {
            padding: 0;
            border: none;
            background: transparent;
        }
        
        .sidebar listbox row:selected {
            background-color: #4a90d9;
            color: white;
        }
        
        .sidebar listbox row:hover {
            background-color: #e8e8e8;
        }
        
        .sidebar listbox row:selected:hover {
            background-color: #4a90d9;
        }
        
        .destructive-action {
            background-color: #e74c3c;
            color: white;
        }
        
        .destructive-action:hover {
            background-color: #c0392b;
        }

        .warning-action {
            background-color: #f39c12;
            color: white;
        }

        .warning-action:hover {
            background-color: #d68910;
        }
        """
        
        css_provider.load_from_data(css.encode())
        screen = self.get_screen()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _setup_ui(self):
        """Configura la interfaz de usuario principal"""
        # HeaderBar
        self._setup_header_bar()
        
        # Layout principal con barra lateral
        main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(main_paned)
        
        # Barra lateral izquierda
        self._setup_sidebar(main_paned)
        
        # Área de contenido principal
        self._setup_content_area(main_paned)

    def _setup_header_bar(self):
        """Configura la barra de encabezado"""
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)
        self.set_titlebar(header_bar)

        # Server Selector
        self.header_server_selector = Gtk.ComboBoxText()
        self.header_server_selector.append_text("-- Add New Server --")
        self.header_server_selector.set_active(0)
        self.header_server_selector.connect("changed", self._on_header_server_selected)
        header_bar.set_custom_title(self.header_server_selector)

        # Control buttons
        self.header_start_button = Gtk.Button(label="Start")
        self.header_start_button.connect("clicked", self._on_start_server_clicked)
        header_bar.pack_end(self.header_start_button)

        self.header_stop_button = Gtk.Button(label="Stop")
        self.header_stop_button.connect("clicked", self._on_stop_server_clicked)
        header_bar.pack_end(self.header_stop_button)

        self.header_kill_button = Gtk.Button(label="Kill")
        self.header_kill_button.connect("clicked", self._on_kill_server_clicked)
        header_bar.pack_end(self.header_kill_button)

        # Estado inicial de botones
        self._update_header_buttons()

    def _setup_sidebar(self, main_paned):
        """Configura la barra lateral izquierda"""
        # Contenedor de la barra lateral
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_box.set_size_request(200, -1)  # Ancho fijo de 200px
        
        # Estilo para la barra lateral
        sidebar_box.get_style_context().add_class("sidebar")
        
        # Lista de elementos de navegación
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        # No conectar la señal aquí todavía
        
        # Elementos de la barra lateral
        self.server_row = self._create_sidebar_row("Server Management", "applications-system")
        self.plugin_row = self._create_sidebar_row("Plugin Manager", "application-x-addon")
        
        self.sidebar_list.add(self.server_row)
        self.sidebar_list.add(self.plugin_row)
        
        sidebar_box.pack_start(self.sidebar_list, False, False, 0)
        
        # Separador
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        
        main_paned.pack1(sidebar_box, False, False)
        
    def _create_sidebar_row(self, label_text, icon_name):
        """Crea una fila para la barra lateral"""
        row = Gtk.ListBoxRow()
        row.page_name = label_text  # Usar atributo Python normal
        
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_margin_left(12)
        hbox.set_margin_right(12)
        hbox.set_margin_top(8)
        hbox.set_margin_bottom(8)
        
        # Icono
        try:
            icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.BUTTON)
        except:
            # Fallback si no existe el icono
            icon = Gtk.Label(label="•")
        
        hbox.pack_start(icon, False, False, 0)
        
        # Label
        label = Gtk.Label(label=label_text)
        label.set_halign(Gtk.Align.START)
        hbox.pack_start(label, True, True, 0)
        
        row.add(hbox)
        return row

    def _setup_content_area(self, main_paned):
        """Configura el área de contenido principal"""
        # Stack para cambiar entre páginas
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.content_stack.set_transition_duration(200)
        
        # Crear las páginas
        self._create_server_management_page()
        self._create_plugin_manager_page()
        
        main_paned.pack2(self.content_stack, True, False)
        
        # Ahora que todo está configurado, conectar la señal y hacer selección inicial
        self.sidebar_list.connect("row-selected", self._on_sidebar_selection_changed)
        self.sidebar_list.select_row(self.server_row)
        self.content_stack.set_visible_child_name("server_management")

    def _on_sidebar_selection_changed(self, listbox, row):
        """Maneja cambios en la selección de la barra lateral"""
        if row is None or not hasattr(self, 'content_stack'):
            return
            
        page_name = row.page_name  # Usar atributo Python normal
        if page_name == "Server Management":
            self.content_stack.set_visible_child_name("server_management")
        elif page_name == "Plugin Manager":
            self.content_stack.set_visible_child_name("plugin_manager")

    def _create_server_management_page(self):
        """Crea la página de gestión de servidores"""
        server_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        server_page.set_margin_left(12)
        server_page.set_margin_right(12)
        server_page.set_margin_top(12)
        server_page.set_margin_bottom(12)

        # Título de la página
        title_label = Gtk.Label()
        title_label.set_markup("<b>Server Management</b>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_margin_bottom(12)
        server_page.pack_start(title_label, False, False, 0)

        # Sección de configuración del servidor
        self._setup_server_configuration_section(server_page)

        # Consola (sección principal)
        self._setup_console_view(server_page)
        
        self.content_stack.add_named(server_page, "server_management")

    def _create_plugin_manager_page(self):
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
        
        self.content_stack.add_named(plugin_page, "plugin_manager")

    def _setup_server_configuration_section(self, container):
        """Configura la sección de configuración del servidor"""
        # Frame para la configuración del servidor
        config_frame = Gtk.Frame(label="Server Configuration")
        container.pack_start(config_frame, False, False, 0)
        
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_box.set_margin_left(12)
        config_box.set_margin_right(12)
        config_box.set_margin_top(12)
        config_box.set_margin_bottom(12)
        config_frame.add(config_box)
        
        # Información del servidor seleccionado
        self.server_info_label = Gtk.Label()
        self.server_info_label.set_markup("<i>Select a server from the title bar to configure</i>")
        self.server_info_label.set_halign(Gtk.Align.START)
        config_box.pack_start(self.server_info_label, False, False, 0)
        
        # Grid para los campos de configuración
        config_grid = Gtk.Grid()
        config_grid.set_column_spacing(12)
        config_grid.set_row_spacing(8)
        config_box.pack_start(config_grid, False, False, 0)
        
        # Server Name
        name_label = Gtk.Label(label="Server Name:")
        name_label.set_halign(Gtk.Align.END)
        self.server_name_entry = Gtk.Entry()
        self.server_name_entry.set_sensitive(False)
        self.server_name_entry.connect("changed", self._on_server_name_changed)
        
        config_grid.attach(name_label, 0, 0, 1, 1)
        config_grid.attach(self.server_name_entry, 1, 0, 2, 1)
        
        # Server Path
        path_label = Gtk.Label(label="Server Path:")
        path_label.set_halign(Gtk.Align.END)
        self.server_path_entry = Gtk.Entry()
        self.server_path_entry.set_sensitive(False)
        self.server_path_entry.set_editable(False)  # Solo lectura
        
        config_grid.attach(path_label, 0, 1, 1, 1)
        config_grid.attach(self.server_path_entry, 1, 1, 2, 1)
        
        # JAR File
        jar_label = Gtk.Label(label="JAR File:")
        jar_label.set_halign(Gtk.Align.END)
        self.server_jar_combo = Gtk.ComboBoxText()
        self.server_jar_combo.set_sensitive(False)
        self.server_jar_combo.connect("changed", self._on_server_jar_changed)
        
        config_grid.attach(jar_label, 0, 2, 1, 1)
        config_grid.attach(self.server_jar_combo, 1, 2, 1, 1)
        
        # Botón para descargar JAR
        self.download_jar_button = Gtk.Button(label="Download JAR")
        self.download_jar_button.set_sensitive(False)
        self.download_jar_button.connect("clicked", self._on_download_jar_clicked)
        config_grid.attach(self.download_jar_button, 2, 2, 1, 1)
        
        # Botones de acción
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        action_box.set_halign(Gtk.Align.CENTER)
        config_box.pack_start(action_box, False, False, 12)
        
        self.save_config_button = Gtk.Button(label="Save Configuration")
        self.save_config_button.set_sensitive(False)
        self.save_config_button.connect("clicked", self._on_save_config_clicked)
        action_box.pack_start(self.save_config_button, False, False, 0)
        
        self.refresh_jars_button = Gtk.Button(label="Refresh JARs")
        self.refresh_jars_button.set_sensitive(False)
        self.refresh_jars_button.connect("clicked", self._on_refresh_jars_clicked)
        action_box.pack_start(self.refresh_jars_button, False, False, 0)
        
        # Separador
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        action_box.pack_start(separator, False, False, 6)
        
        # Botones de gestión del servidor
        self.unlink_server_button = Gtk.Button(label="Unlink Server")
        self.unlink_server_button.set_sensitive(False)
        self.unlink_server_button.get_style_context().add_class("warning-action")
        self.unlink_server_button.connect("clicked", self._on_unlink_server_clicked)
        action_box.pack_start(self.unlink_server_button, False, False, 0)
        
        self.delete_server_button = Gtk.Button(label="Delete Server")
        self.delete_server_button.set_sensitive(False)
        self.delete_server_button.get_style_context().add_class("destructive-action")
        self.delete_server_button.connect("clicked", self._on_delete_server_clicked)
        action_box.pack_start(self.delete_server_button, False, False, 0)

    def _setup_console_view(self, container):
        """Configura la vista de consola"""
        self.console_buffer = Gtk.TextBuffer()
        self.console_view = Gtk.TextView(buffer=self.console_buffer)
        self.console_view.set_editable(False)
        self.console_view.set_cursor_visible(False)

        self.console_scrolled_window = Gtk.ScrolledWindow()
        self.console_scrolled_window.set_hexpand(True)
        self.console_scrolled_window.set_vexpand(True)
        self.console_scrolled_window.add(self.console_view)
        container.pack_start(self.console_scrolled_window, True, True, 0)

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

    def _setup_console(self):
        """Configura la consola y auto-scroll"""
        self.console_adjustment = self.console_scrolled_window.get_vadjustment()

    def _load_initial_data(self):
        """Carga los datos iniciales"""
        self.server_controller.load_servers()
        self._refresh_server_list()
        self._log_to_console("Welcome to the Minecraft Server Manager console!\n")
        self._log_to_console("Server output will appear here.\n")

    # Event Handlers - Server Configuration
    def _on_server_name_changed(self, entry):
        """Maneja cambios en el nombre del servidor"""
        if self.selected_server and entry.get_text():
            self.save_config_button.set_sensitive(True)

    def _on_server_jar_changed(self, combo):
        """Maneja cambios en la selección del JAR"""
        if self.selected_server:
            self.save_config_button.set_sensitive(True)

    def _on_download_jar_clicked(self, widget):
        """Maneja el clic en descargar JAR"""
        if not self.selected_server:
            self._log_to_console("Please select a server first.\n")
            return

        dialog = DownloadServerDialog(self)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            details = dialog.get_download_details()
            if details["type"] == "Paper" and details["version"]:
                self._start_download(details["version"])

        dialog.destroy()

    def _on_save_config_clicked(self, widget):
        """Maneja el clic en guardar configuración"""
        if not self.selected_server:
            return

        # Actualizar nombre del servidor
        new_name = self.server_name_entry.get_text()
        if new_name and new_name != self.selected_server.name:
            old_name = self.selected_server.name
            self.selected_server.name = new_name
            
            # Actualizar en el header selector
            self._refresh_server_list()
            self._select_server_by_name(new_name)
            
            self._log_to_console(f"Server name changed from '{old_name}' to '{new_name}'\n")

        # Actualizar JAR seleccionado
        selected_jar = self.server_jar_combo.get_active_text()
        if selected_jar and selected_jar != self.selected_server.jar:
            old_jar = self.selected_server.jar
            self.server_controller.update_server_jar(self.selected_server, selected_jar)
            self._log_to_console(f"Server JAR changed from '{old_jar}' to '{selected_jar}'\n")

        # Guardar cambios
        if self.server_controller.save_servers():
            self._log_to_console("Server configuration saved successfully.\n")
            self.save_config_button.set_sensitive(False)
            self._update_header_buttons()
        else:
            self._log_to_console("Error saving server configuration.\n")

    def _on_refresh_jars_clicked(self, widget):
        """Maneja el clic en refrescar JARs"""
        if self.selected_server:
            self._update_jar_list()
            self._log_to_console("JAR list refreshed.\n")

    def _on_unlink_server_clicked(self, widget):
        """Maneja el clic en desvincular servidor"""
        if not self.selected_server:
            return

        # Diálogo de confirmación
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"Unlink Server '{self.selected_server.name}'?"
        )
        dialog.format_secondary_text(
            "This will remove the server from the manager but will NOT delete "
            "the server files from your disk. The server data will remain intact."
        )

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            server_name = self.selected_server.name
            self._unlink_server(self.selected_server)
            self._log_to_console(f"Server '{server_name}' has been unlinked from the manager.\n")

    def _on_delete_server_clicked(self, widget):
        """Maneja el clic en eliminar servidor"""
        if not self.selected_server:
            return

        # Diálogo de confirmación más estricto
        dialog = Gtk.MessageDialog(
            parent=self,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"DELETE Server '{self.selected_server.name}'?"
        )
        dialog.format_secondary_text(
            "⚠️  WARNING: This will PERMANENTLY DELETE all server files from your disk!\n\n"
            f"Server path: {self.selected_server.path}\n\n"
            "This action CANNOT be undone. All worlds, configurations, and plugins will be lost.\n\n"
            "Are you absolutely sure you want to continue?"
        )

        # Hacer el botón YES más prominente para la advertencia
        dialog.set_default_response(Gtk.ResponseType.NO)

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            # Segundo diálogo de confirmación
            confirm_dialog = Gtk.MessageDialog(
                parent=self,
                flags=Gtk.DialogFlags.MODAL,
                message_type=Gtk.MessageType.ERROR,
                buttons=Gtk.ButtonsType.YES_NO,
                text="Final Confirmation"
            )
            confirm_dialog.format_secondary_text(
                f"Type the server name '{self.selected_server.name}' to confirm deletion:"
            )
            
            # Añadir campo de entrada para confirmación
            content_area = confirm_dialog.get_content_area()
            entry = Gtk.Entry()
            entry.set_placeholder_text("Enter server name to confirm")
            content_area.pack_start(entry, False, False, 0)
            content_area.show_all()

            final_response = confirm_dialog.run()
            entered_name = entry.get_text()
            confirm_dialog.destroy()

            if (final_response == Gtk.ResponseType.YES and 
                entered_name == self.selected_server.name):
                server_name = self.selected_server.name
                server_path = self.selected_server.path
                
                if self._delete_server(self.selected_server):
                    self._log_to_console(f"Server '{server_name}' and all its files have been permanently deleted from '{server_path}'.\n")
                else:
                    self._log_to_console(f"Error: Could not delete server '{server_name}'. Check permissions and try again.\n")
            else:
                self._log_to_console("Server deletion cancelled - name confirmation failed.\n")

    # Event Handlers - Server Management
    def _on_header_server_selected(self, combobox):
        """Maneja la selección de servidor en el header"""
        selected_name = combobox.get_active_text()
        if not selected_name:
            return

        if selected_name == "-- Add New Server --":
            self._show_add_server_dialog()
            # Resetear a servidor anterior si existe
            if self.selected_server:
                self._update_header_selector(self.selected_server.name)
            else:
                combobox.set_active(0)
            return

        # Buscar y seleccionar servidor
        server = self.server_controller.find_server_by_name(selected_name)
        if server:
            self._select_server(server)

    def _on_server_selection_changed(self, selection=None):
        """Maneja cambios en la selección de servidores - ahora solo desde header"""
        # Esta función ya no se usa para TreeView, solo mantenemos compatibilidad
        # La selección ahora se maneja completamente a través del header selector
        pass

    def _show_add_server_dialog(self):
        """Muestra el diálogo para añadir un nuevo servidor"""
        dialog = AddServerDialog(self)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            details = dialog.get_server_details()
            if self.server_controller.add_server(
                details["name"], details["path"], details["jar"]
            ):
                self._refresh_server_list()
                # Seleccionar el nuevo servidor
                new_server = self.server_controller.find_server_by_name(details["name"])
                if new_server:
                    self._select_server_by_name(details["name"])
        
        dialog.destroy()

    def _on_start_server_clicked(self, widget):
        """Maneja el clic en iniciar servidor"""
        if not self.selected_server:
            return

        # Verificar EULA si es necesario
        if not self._check_and_handle_eula():
            return

        self.server_controller.start_server(self.selected_server)
        self._update_header_buttons()

    def _on_stop_server_clicked(self, widget):
        """Maneja el clic en detener servidor"""
        if self.selected_server:
            self.server_controller.stop_server(self.selected_server)

    def _on_kill_server_clicked(self, widget):
        """Maneja el clic en matar servidor"""
        if self.selected_server:
            self.server_controller.kill_server(self.selected_server)

    # Event Handlers - Plugin Management
    def _on_add_local_plugin_clicked(self, widget):
        """Maneja el clic en añadir plugin local"""
        if not self.selected_server:
            self._log_to_console("Please select a server first.\n")
            return

        dialog = Gtk.FileChooserDialog(
            title="Select Plugin JAR File",
            parent=self,
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
            self._log_to_console("Please select a plugin to remove.\n")
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
            self._log_to_console("Please enter a search query.\n")
            return

        self.online_search_store.clear()
        self.plugin_controller.search_modrinth_plugins(query, self._on_search_results)

    def _on_download_online_plugin_clicked(self, widget):
        """Maneja el clic en descargar plugin online"""
        self._log_to_console("Download Online Plugin functionality not yet implemented.\n")

    def _on_update_online_plugin_clicked(self, widget):
        """Maneja el clic en actualizar plugin online"""
        self._log_to_console("Update Online Plugin functionality not yet implemented.\n")

    def _unlink_server(self, server: MinecraftServer) -> bool:
        """Desvincula un servidor de la gestión (no elimina archivos)"""
        try:
            # Usar el método del controlador
            success = self.server_controller.remove_server(server)
            
            if success:
                # Actualizar interfaz
                self._refresh_server_list()
                
                # Limpiar selección actual
                self.selected_server = None
                self._update_header_buttons()
                self._clear_server_configuration()
                self._update_plugin_info(None)
            
            return success
            
        except Exception as e:
            self._log_to_console(f"Error unlinking server: {e}\n")
            return False

    def _delete_server(self, server: MinecraftServer) -> bool:
        """Elimina completamente un servidor y todos sus archivos"""
        try:
            import shutil
            
            # Detener el servidor si está ejecutándose
            if self.server_controller.is_server_running(server):
                self.server_controller.kill_server(server)
                # Esperar un momento para que el proceso termine
                import time
                time.sleep(1)
            
            # Eliminar directorio del servidor
            if os.path.exists(server.path):
                shutil.rmtree(server.path)
                self._log_to_console(f"Deleted server directory: {server.path}\n")
            
            # Usar el método del controlador para eliminar de la lista
            success = self.server_controller.remove_server(server)
            
            if success:
                # Actualizar interfaz
                self._refresh_server_list()
                
                # Limpiar selección actual
                self.selected_server = None
                self._update_header_buttons()
                self._clear_server_configuration()
                self._update_plugin_info(None)
            
            return success
            
        except Exception as e:
            self._log_to_console(f"Error deleting server: {e}\n")
            return False

    # Utility Methods
    def _select_server(self, server: MinecraftServer):
        """Selecciona un servidor"""
        self.selected_server = server
        self._update_header_buttons()
        self._update_plugin_info(server)
        self._update_server_configuration(server)
        self.plugin_controller.refresh_local_plugins(server.path)

    def _update_server_configuration(self, server: MinecraftServer):
        """Actualiza los campos de configuración del servidor"""
        if not hasattr(self, 'server_name_entry'):
            return  # Los widgets aún no están creados
            
        # Actualizar información del servidor
        self.server_info_label.set_markup(f"<b>Configuring:</b> {server.name}")
        
        # Actualizar campos
        self.server_name_entry.set_text(server.name)
        self.server_path_entry.set_text(server.path)
        
        # Actualizar lista de JARs
        self._update_jar_list()
        
        # Habilitar controles
        self.server_name_entry.set_sensitive(True)
        self.server_jar_combo.set_sensitive(True)
        self.download_jar_button.set_sensitive(True)
        self.save_config_button.set_sensitive(False)  # Solo si hay cambios
        self.refresh_jars_button.set_sensitive(True)
        self.unlink_server_button.set_sensitive(True)
        self.delete_server_button.set_sensitive(True)

    def _update_jar_list(self):
        """Actualiza la lista de JARs disponibles"""
        if not self.selected_server or not hasattr(self, 'server_jar_combo'):
            return
            
        self.server_jar_combo.remove_all()
        self.server_jar_combo.append_text("DOWNLOAD_LATER")
        
        # Buscar archivos JAR en el directorio del servidor
        from utils.file_utils import get_jar_files_in_directory
        jar_files = get_jar_files_in_directory(self.selected_server.path)
        
        for jar_file in jar_files:
            self.server_jar_combo.append_text(jar_file)
        
        # Seleccionar el JAR actual
        current_jar = self.selected_server.jar
        for i in range(self.server_jar_combo.get_model().iter_n_children(None)):
            if self.server_jar_combo.get_model().get_value(
                self.server_jar_combo.get_model().get_iter_from_string(str(i)), 0
            ) == current_jar:
                self.server_jar_combo.set_active(i)
                break
        else:
            # Si no se encuentra, seleccionar "DOWNLOAD_LATER"
            self.server_jar_combo.set_active(0)

    def _select_server_by_name(self, name: str):
        """Selecciona un servidor por nombre en el header selector"""
        # Buscar y seleccionar en el header selector
        for i in range(self.header_server_selector.get_model().iter_n_children(None)):
            if self.header_server_selector.get_model().get_value(
                self.header_server_selector.get_model().get_iter_from_string(str(i)), 0
            ) == name:
                self.header_server_selector.set_active(i)
                break

    def _update_header_selector(self, server_name: str):
        """Actualiza el selector del header"""
        # Buscar el índice del servidor
        for i in range(self.header_server_selector.get_model().iter_n_children(None)):
            if self.header_server_selector.get_model().get_value(
                self.header_server_selector.get_model().get_iter_from_string(str(i)), 0
            ) == server_name:
                self.header_server_selector.set_active(i)
                break

    def _update_header_buttons(self):
        """Actualiza el estado de los botones del header"""
        if self.selected_server:
            is_running = self.server_controller.is_server_running(self.selected_server)
            can_start = not is_running and self.selected_server.has_jar_file()
            
            self.header_start_button.set_sensitive(can_start)
            self.header_stop_button.set_sensitive(is_running)
            self.header_kill_button.set_sensitive(is_running)
        else:
            self.header_start_button.set_sensitive(False)
            self.header_stop_button.set_sensitive(False)
            self.header_kill_button.set_sensitive(False)

    def _update_plugin_info(self, server: MinecraftServer):
        """Actualiza la información de plugins"""
        if server:
            self.plugin_server_label.set_text(f"Managing plugins for: {server.name}")
        else:
            self.plugin_server_label.set_text("Select a server to manage plugins.")
            # También limpiar configuración del servidor
            self._clear_server_configuration()

    def _clear_server_configuration(self):
        """Limpia los campos de configuración cuando no hay servidor seleccionado"""
        if not hasattr(self, 'server_name_entry'):
            return
            
        self.server_info_label.set_markup("<i>Select a server from the title bar to configure</i>")
        self.server_name_entry.set_text("")
        self.server_path_entry.set_text("")
        self.server_jar_combo.remove_all()
        
        # Deshabilitar controles
        self.server_name_entry.set_sensitive(False)
        self.server_jar_combo.set_sensitive(False)
        self.download_jar_button.set_sensitive(False)
        self.save_config_button.set_sensitive(False)
        self.refresh_jars_button.set_sensitive(False)
        self.unlink_server_button.set_sensitive(False)
        self.delete_server_button.set_sensitive(False)

    def _refresh_server_list(self):
        """Refresca el selector de servidores del header"""
        self.header_server_selector.remove_all()
        self.header_server_selector.append_text("-- Add New Server --")

        servers = self.server_controller.get_servers()
        for server in servers:
            self.header_server_selector.append_text(server.name)

        if servers:
            self.header_server_selector.set_active(1)  # Seleccionar primer servidor
        else:
            self.header_server_selector.set_active(0)

    def _log_to_console(self, message: str):
        """Añade un mensaje a la consola con auto-scroll"""
        # Verificar si estamos al final
        at_bottom = False
        if self.console_adjustment.get_upper() > 0:
            current = self.console_adjustment.get_value()
            page_size = self.console_adjustment.get_page_size()
            upper = self.console_adjustment.get_upper()
            if current + page_size >= upper:
                at_bottom = True

        # Insertar texto
        self.console_buffer.insert_at_cursor(message)

        # Auto-scroll si estábamos al final
        if at_bottom:
            self.console_adjustment.set_value(self.console_adjustment.get_upper())

    def _check_and_handle_eula(self) -> bool:
        """Verifica y maneja el EULA si es necesario"""
        if not self.selected_server:
            return False

        eula_path = f"{self.selected_server.path}/eula.txt"
        if not self.server_controller._check_eula(self.selected_server):
            dialog = EulaDialog(self, self.selected_server.name)
            if dialog.run_and_get_response():
                return self.server_controller.accept_eula(self.selected_server)
            return False
        return True

    def _start_download(self, version: str):
        """Inicia la descarga de un JAR"""
        if not self.selected_server:
            return

        def on_download_success(jar_filename):
            self.server_controller.update_server_jar(self.selected_server, jar_filename)
            self._refresh_server_list()
            self._update_header_buttons()

        self.download_controller.download_paper_jar(
            version, 
            self.selected_server.path, 
            on_download_success
        )

    # Callbacks from Controllers
    def _on_server_finished(self, server_path: str, exit_code: int):
        """Callback cuando un servidor termina"""
        self._update_header_buttons()

    def _on_plugins_updated(self, plugins):
        """Callback cuando se actualizan los plugins"""
        self.local_plugin_store.clear()
        for plugin in plugins:
            self.local_plugin_store.append([plugin.name, plugin.file_path or ""])

    def _on_search_results(self, plugins):
        """Callback con resultados de búsqueda"""
        self.online_search_store.clear()
        for plugin in plugins:
            self.online_search_store.append([plugin.name, plugin.source, plugin.version])
