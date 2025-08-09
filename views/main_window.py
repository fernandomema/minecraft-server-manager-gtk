"""
Ventana principal de la aplicación Minecraft Server Manager
"""
import gi
import os
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

_ = gettext.gettext

from controllers.server_controller import ServerController
from controllers.download_controller import DownloadController
from controllers.plugin_controller import PluginController
from views.ui_setup import UISetup
from views.console_manager import ConsoleManager
from views.server_management_page import ServerManagementPage
from views.plugin_management_page import PluginManagementPage
from views.config_editor_page import ConfigEditorPage
from views.log_viewer_page import LogViewerPage
from views.port_analysis_page import PortAnalysisPage
from models.server import MinecraftServer


class MinecraftServerManager(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title=_("Minecraft Server Manager"))
        self.set_default_size(1000, 700)

        # Inicializar controladores
        self._init_controllers()
        
        # Inicializar managers y pages
        self._init_managers()
        
        # Variables de estado
        self.selected_server = None
        
        # Configurar interfaz
        UISetup.setup_css()
        self._setup_ui()
        
        # Cargar datos iniciales
        self._load_initial_data()
        
        self.connect("destroy", Gtk.main_quit)

    def _init_controllers(self):
        """Inicializa los controladores"""
        self.server_controller = ServerController()
        self.download_controller = DownloadController()
        self.plugin_controller = PluginController()

    def _init_managers(self):
        """Inicializa los managers y páginas"""
        # Console manager
        self.console_manager = ConsoleManager()
        
        # Pages
        self.server_management_page = ServerManagementPage(
            self, self.server_controller, self.download_controller, self.console_manager
        )
        self.plugin_management_page = PluginManagementPage(
            self, self.console_manager, self.plugin_controller
        )
        self.config_editor_page = ConfigEditorPage(
            self, self.server_controller, self.console_manager
        )
        self.log_viewer_page = LogViewerPage(self.server_controller)
        self.port_analysis_page = PortAnalysisPage(self.server_controller)
        
        # Configurar callbacks
        self._setup_callbacks()

    def _setup_callbacks(self):
        """Configura los callbacks entre componentes"""
        # Server controller callbacks
        self.server_controller.set_console_callback(self.console_manager.log_to_console)
        self.server_controller.set_server_finished_callback(self._on_server_finished)
        
        # Download controller callbacks
        self.download_controller.set_download_callback(self.console_manager.log_to_console)
        
        # Plugin controller callbacks
        self.plugin_controller.set_search_callback(self.console_manager.log_to_console)
        self.plugin_controller.set_plugins_updated_callback(self.plugin_management_page.on_plugins_updated)

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
        header_callbacks = {
            'on_header_server_selected': self._on_header_server_selected,
            'on_start_server_clicked': self._on_start_server_clicked,
            'on_stop_server_clicked': self._on_stop_server_clicked,
            'on_kill_server_clicked': self._on_kill_server_clicked
        }
        
        header_widgets = UISetup.setup_header_bar(self, header_callbacks)
        
        # Store references to widgets
        self.header_server_selector = header_widgets['header_server_selector']
        self.header_start_button = header_widgets['header_start_button']
        self.header_stop_button = header_widgets['header_stop_button'] 
        self.header_kill_button = header_widgets['header_kill_button']

        # Estado inicial de botones
        self._update_header_buttons()

    def _setup_sidebar(self, main_paned):
        """Configura la barra lateral izquierda"""
        sidebar_callbacks = {
            'on_sidebar_selection_changed': self._on_sidebar_selection_changed
        }
        
        sidebar_widgets = UISetup.setup_sidebar(main_paned, sidebar_callbacks)
        
        # Store references to widgets
        self.sidebar_list = sidebar_widgets['sidebar_list']
        self.server_row = sidebar_widgets['server_row']
        self.plugin_row = sidebar_widgets['plugin_row']
        self.config_row = sidebar_widgets['config_row']
        self.port_row = sidebar_widgets['port_row']
        self.logs_row = sidebar_widgets['logs_row']
        
    def _create_sidebar_row(self, label_text, icon_name):
        """Crea una fila para la barra lateral - DEPRECATED, use UISetup.create_sidebar_row"""
        return UISetup.create_sidebar_row(label_text, icon_name)

    def _setup_content_area(self, main_paned):
        """Configura el área de contenido principal"""
        # Stack para cambiar entre páginas
        self.content_stack = UISetup.setup_content_stack(main_paned)
        
        # Crear las páginas usando los nuevos managers
        server_page = self.server_management_page.create_page()
        plugin_page = self.plugin_management_page.create_page()
        config_page = self.config_editor_page.create_page()
        port_page = self.port_analysis_page.create_page()
        log_page = self.log_viewer_page.create_page()

        self.content_stack.add_named(server_page, "server_management")
        self.content_stack.add_named(plugin_page, "plugin_manager")
        self.content_stack.add_named(config_page, "config_editor")
        self.content_stack.add_named(port_page, "port_analyzer")
        self.content_stack.add_named(log_page, "log_viewer")
        
        # Ahora que todo está configurado, conectar la señal y hacer selección inicial
        self.sidebar_list.connect("row-selected", self._on_sidebar_selection_changed)
        self.sidebar_list.select_row(self.server_row)
        self.content_stack.set_visible_child_name("server_management")

    def _on_sidebar_selection_changed(self, listbox, row):
        """Maneja cambios en la selección de la barra lateral"""
        if row is None or not hasattr(self, 'content_stack'):
            return
            
        page_name = row.page_name  # Usar atributo Python normal
        if page_name == _("Server Management"):
            self.content_stack.set_visible_child_name("server_management")
        elif page_name == _("Plugin Manager"):
            self.content_stack.set_visible_child_name("plugin_manager")
        elif page_name == _("Config Editor"):
            self.content_stack.set_visible_child_name("config_editor")
        elif page_name == _("Port Analyzer"):
            self.content_stack.set_visible_child_name("port_analyzer")
        elif page_name == _("Logs"):
            self.content_stack.set_visible_child_name("log_viewer")

    def _load_initial_data(self):
        """Carga los datos iniciales"""
        self.server_controller.load_servers()
        self._refresh_server_list()
        self.console_manager.log_to_console(_("Welcome to the Minecraft Server Manager console!\n"))
        self.console_manager.log_to_console(_("Server output will appear here.\n"))

    # Event Handlers - delegated to page classes
    def _on_header_server_selected(self, combobox):
        """Maneja la selección de servidor en el header"""
        selected_name = combobox.get_active_text()
        if not selected_name:
            return

        if selected_name == _("-- Add New Server --"):
            self.server_management_page.show_add_server_dialog()
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

    def _on_start_server_clicked(self, widget):
        """Maneja el clic en iniciar servidor"""
        self.server_management_page.start_server()

    def _on_stop_server_clicked(self, widget):
        """Maneja el clic en detener servidor"""
        self.server_management_page.stop_server()

    def _on_kill_server_clicked(self, widget):
        """Maneja el clic en matar servidor"""
        self.server_management_page.kill_server()

    # Utility Methods - simplified coordination
    def _select_server(self, server: MinecraftServer):
        """Selecciona un servidor"""
        self.selected_server = server
        self._update_header_buttons()
        
        # Notificar a las páginas
        self.server_management_page.select_server(server)
        self.plugin_management_page.select_server(server)
        self.config_editor_page.select_server(server)
        self.port_analysis_page.select_server(server)
        self.log_viewer_page.select_server(server)

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

    def _refresh_server_list(self):
        """Refresca el selector de servidores del header"""
        self.header_server_selector.remove_all()
        self.header_server_selector.append_text(_("-- Add New Server --"))

        servers = self.server_controller.get_servers()
        for server in servers:
            self.header_server_selector.append_text(server.name)

        if servers:
            self.header_server_selector.set_active(1)  # Seleccionar primer servidor
        else:
            self.header_server_selector.set_active(0)

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

    # Callbacks from Controllers
    def _on_server_finished(self, server_path: str, exit_code: int):
        """Callback cuando un servidor termina"""
        self._update_header_buttons()
