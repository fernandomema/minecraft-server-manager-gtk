"""
Ventana principal de la aplicación Minecraft Server Manager
"""
import gi
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

        # Sección superior: Solo botones de acción
        hbox_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        server_page.pack_start(hbox_top, False, False, 0)

        # Botones de acción (centrados)
        self._setup_server_buttons(hbox_top)

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

    def _setup_server_buttons(self, container):
        """Configura los botones de acción de servidor"""
        # Centrar los botones horizontalmente
        button_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_hbox.set_halign(Gtk.Align.CENTER)
        container.pack_start(button_hbox, True, False, 0)

        self.add_server_button = Gtk.Button(label="Add Server")
        self.add_server_button.connect("clicked", self._on_add_server_clicked)
        button_hbox.pack_start(self.add_server_button, False, False, 0)

        self.download_server_button = Gtk.Button(label="Download Server Type")
        self.download_server_button.connect("clicked", self._on_download_server_clicked)
        button_hbox.pack_start(self.download_server_button, False, False, 0)

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

    # Event Handlers - Server Management
    def _on_header_server_selected(self, combobox):
        """Maneja la selección de servidor en el header"""
        selected_name = combobox.get_active_text()
        if not selected_name:
            return

        if selected_name == "-- Add New Server --":
            self._on_add_server_clicked(None)
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

    def _on_add_server_clicked(self, widget):
        """Maneja el clic en añadir servidor"""
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

    def _on_download_server_clicked(self, widget):
        """Maneja el clic en descargar servidor"""
        if not self.selected_server:
            self._log_to_console("Please select a server to download a JAR for.\n")
            return

        dialog = DownloadServerDialog(self)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            details = dialog.get_download_details()
            if details["type"] == "Paper" and details["version"]:
                self._start_download(details["version"])

        dialog.destroy()

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

    # Utility Methods
    def _select_server(self, server: MinecraftServer):
        """Selecciona un servidor"""
        self.selected_server = server
        self._update_header_buttons()
        self._update_plugin_info(server)
        self.plugin_controller.refresh_local_plugins(server.path)

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
