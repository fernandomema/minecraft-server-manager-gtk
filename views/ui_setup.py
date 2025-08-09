"""
UI Setup utilities for the Minecraft Server Manager
Contains methods for setting up common UI components
"""
import gi
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

_ = gettext.gettext


class UISetup:
    """Utility class for common UI setup operations"""
    
    @staticmethod
    def setup_css():
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

        .content {
            background-color: @theme_base_color;
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
        screen = Gdk.Screen.get_default()
        style_context = Gtk.StyleContext()
        style_context.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    @staticmethod
    def create_sidebar_row(label_text, icon_name):
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

    @staticmethod
    def setup_header_bar(window, callbacks):
        """Configura la barra de encabezado"""
        header_bar = Gtk.HeaderBar()
        header_bar.set_show_close_button(True)
        window.set_titlebar(header_bar)

        # Server Selector
        header_server_selector = Gtk.ComboBoxText()
        header_server_selector.append_text(_("-- Add New Server --"))
        header_server_selector.set_active(0)
        header_server_selector.connect("changed", callbacks['on_header_server_selected'])
        header_bar.set_custom_title(header_server_selector)

        # Control buttons
        buttons_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        buttons_box.get_style_context().add_class("linked")

        header_start_button = Gtk.Button.new_from_icon_name(
            "media-playback-start-symbolic", Gtk.IconSize.BUTTON
        )
        header_start_button.connect("clicked", callbacks['on_start_server_clicked'])
        buttons_box.pack_start(header_start_button, False, False, 0)

        header_stop_button = Gtk.Button.new_from_icon_name(
            "media-playback-stop-symbolic", Gtk.IconSize.BUTTON
        )
        header_stop_button.connect("clicked", callbacks['on_stop_server_clicked'])
        buttons_box.pack_start(header_stop_button, False, False, 0)

        header_kill_button = Gtk.Button.new_from_icon_name(
            "process-stop-symbolic", Gtk.IconSize.BUTTON
        )
        header_kill_button.connect("clicked", callbacks['on_kill_server_clicked'])
        buttons_box.pack_start(header_kill_button, False, False, 0)

        header_bar.pack_end(buttons_box)

        return {
            'header_server_selector': header_server_selector,
            'header_start_button': header_start_button,
            'header_stop_button': header_stop_button,
            'header_kill_button': header_kill_button
        }

    @staticmethod
    def setup_sidebar(main_paned, callbacks):
        """Configura la barra lateral izquierda"""
        # Contenedor de la barra lateral
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_box.set_size_request(200, -1)  # Ancho fijo de 200px
        
        # Estilo para la barra lateral
        sidebar_box.get_style_context().add_class("sidebar")
        
        # Lista de elementos de navegación
        sidebar_list = Gtk.ListBox()
        sidebar_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        
        # Elementos de la barra lateral
        server_row = UISetup.create_sidebar_row(_("Server Management"), "applications-system")
        plugin_row = UISetup.create_sidebar_row(_("Plugin Manager"), "application-x-addon")
        player_row = UISetup.create_sidebar_row(_("Player Management"), "system-users")
        resource_row = UISetup.create_sidebar_row(_("Resource Packs"), "package-x-generic")
        config_row = UISetup.create_sidebar_row(_("Config Editor"), "preferences-system")
        port_row = UISetup.create_sidebar_row(_("Port Analyzer"), "network-server")
        logs_row = UISetup.create_sidebar_row(_("Logs"), "text-x-log")

        sidebar_list.add(server_row)
        sidebar_list.add(plugin_row)
        sidebar_list.add(player_row)
        sidebar_list.add(resource_row)
        sidebar_list.add(config_row)
        sidebar_list.add(port_row)
        sidebar_list.add(logs_row)

        sidebar_box.pack_start(sidebar_list, True, True, 0)  # Asegurando que la lista ocupe espacio en el contenedor

        # Separador
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        main_paned.pack1(sidebar_box, False, False)  # Asegurando que la barra lateral se agregue al diseño principal

        return {
            'sidebar_list': sidebar_list,
            'server_row': server_row,
            'plugin_row': plugin_row,
            'player_row': player_row,
            'resource_row': resource_row,
            'config_row': config_row,
            'port_row': port_row,
            'logs_row': logs_row
        }

    @staticmethod
    def setup_content_stack(main_paned):
        """Configura el stack de contenido principal"""
        # Stack para cambiar entre páginas
        content_stack = Gtk.Stack()
        content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        content_stack.set_transition_duration(200)
        content_stack.get_style_context().add_class("content")

        main_paned.pack2(content_stack, True, False)

        return content_stack
