"""
Config Editor Page for the Minecraft Server Manager
Visual editor for YAML configuration files with help tooltips
"""
import gi
import os
import yaml
import re
from typing import Dict, Any, List, Tuple
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GObject, Pango


class ConfigEditorPage:
    """Handles visual editing of YAML configuration files"""
    
    def __init__(self, parent_window, server_controller, console_manager):
        self.parent_window = parent_window
        self.server_controller = server_controller
        self.console_manager = console_manager
        self.selected_server = None
        self.current_file = None
        self.config_data = {}
        self.widgets = {}  # Store widgets for each config key
        self.file_tree = None
        self.config_container = None
        self.unsaved_changes = False

    def create_page(self):
        """Crea la página del editor de configuración"""
        config_page = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        config_page.set_margin_left(12)
        config_page.set_margin_right(12)
        config_page.set_margin_top(12)
        config_page.set_margin_bottom(12)

        # Panel izquierdo: Lista de archivos de configuración
        self._setup_file_panel(config_page)

        # Panel derecho: Editor de configuración
        self._setup_editor_panel(config_page)

        return config_page

    def _setup_file_panel(self, container):
        """Configura el panel de archivos de configuración"""
        # Frame para la lista de archivos
        file_frame = Gtk.Frame(label="Configuration Files")
        file_frame.set_size_request(250, -1)
        container.pack_start(file_frame, False, False, 0)
        
        file_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        file_box.set_margin_left(6)
        file_box.set_margin_right(6)
        file_box.set_margin_top(6)
        file_box.set_margin_bottom(6)
        file_frame.add(file_box)
        
        # Información del servidor seleccionado
        self.server_info_label = Gtk.Label()
        self.server_info_label.set_markup("<i>Select a server to view config files</i>")
        self.server_info_label.set_halign(Gtk.Align.START)
        file_box.pack_start(self.server_info_label, False, False, 0)
        
        # TreeView para archivos de configuración
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.set_vexpand(True)
        file_box.pack_start(scrolled_window, True, True, 0)
        
        # Modelo y vista del árbol
        self.file_store = Gtk.TreeStore(str, str)  # Nombre visible, ruta completa
        self.file_tree = Gtk.TreeView(model=self.file_store)
        self.file_tree.set_headers_visible(False)
        
        # Columna para nombre del archivo
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("File", renderer, text=0)
        self.file_tree.append_column(column)
        
        # Conectar señal de selección
        selection = self.file_tree.get_selection()
        selection.connect("changed", self._on_file_selected)
        
        scrolled_window.add(self.file_tree)
        
        # Botones de acción
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        file_box.pack_start(button_box, False, False, 0)
        
        self.refresh_button = Gtk.Button(label="Refresh")
        self.refresh_button.set_sensitive(False)
        self.refresh_button.connect("clicked", self._on_refresh_files)
        button_box.pack_start(self.refresh_button, False, False, 0)
        
        self.save_button = Gtk.Button(label="Save")
        self.save_button.set_sensitive(False)
        self.save_button.connect("clicked", self._on_save_config)
        button_box.pack_start(self.save_button, False, False, 0)

    def _setup_editor_panel(self, container):
        """Configura el panel del editor de configuración"""
        # Frame para el editor
        editor_frame = Gtk.Frame(label="Configuration Editor")
        container.pack_start(editor_frame, True, True, 0)
        
        editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        editor_box.set_margin_left(6)
        editor_box.set_margin_right(6)
        editor_box.set_margin_top(6)
        editor_box.set_margin_bottom(6)
        editor_frame.add(editor_box)
        
        # Información del archivo actual
        self.file_info_label = Gtk.Label()
        self.file_info_label.set_markup("<i>Select a configuration file to edit</i>")
        self.file_info_label.set_halign(Gtk.Align.START)
        editor_box.pack_start(self.file_info_label, False, False, 0)
        
        # ScrolledWindow para el contenido del editor
        scrolled_editor = Gtk.ScrolledWindow()
        scrolled_editor.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_editor.set_vexpand(True)
        editor_box.pack_start(scrolled_editor, True, True, 0)
        
        # Viewport para el contenido del editor
        viewport = Gtk.Viewport()
        scrolled_editor.add(viewport)
        
        # Container para los campos de configuración
        self.config_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.config_container.set_margin_left(12)
        self.config_container.set_margin_right(12)
        self.config_container.set_margin_top(12)
        self.config_container.set_margin_bottom(12)
        viewport.add(self.config_container)

    def select_server(self, server):
        """Selecciona un servidor y carga sus archivos de configuración"""
        self.selected_server = server
        if server:
            self.server_info_label.set_markup(f"<b>Server:</b> {server.name}")
            self.refresh_button.set_sensitive(True)
            self._load_config_files()
        else:
            self.server_info_label.set_markup("<i>Select a server to view config files</i>")
            self.refresh_button.set_sensitive(False)
            self._clear_file_list()

    def _load_config_files(self):
        """Carga la lista de archivos de configuración del servidor"""
        if not self.selected_server:
            return
            
        self.file_store.clear()
        server_path = self.selected_server.path
        
        # Archivos de configuración comunes de Minecraft
        config_files = [
            "server.properties",
            "bukkit.yml", 
            "spigot.yml",
            "paper.yml",
            "config/paper-global.yml",
            "config/paper-world-defaults.yml"
        ]
        
        # Buscar archivos existentes
        for config_file in config_files:
            file_path = os.path.join(server_path, config_file)
            if os.path.exists(file_path):
                # Determinar la categoría
                if config_file.startswith("config/"):
                    category = "Paper Config"
                    filename = os.path.basename(config_file)
                elif config_file.endswith(".yml"):
                    category = "Server Config"
                    filename = config_file
                else:
                    category = "Properties"
                    filename = config_file
                
                # Buscar o crear categoría
                category_iter = self._find_or_create_category(category)
                
                # Añadir archivo a la categoría
                self.file_store.append(category_iter, [filename, file_path])
        
        # Buscar archivos de configuración de plugins
        self._load_plugin_configs(server_path)
        
        # Expandir todas las categorías
        self.file_tree.expand_all()

    def _find_or_create_category(self, category_name):
        """Busca o crea una categoría en el tree store"""
        # Buscar categoría existente
        for row in self.file_store:
            if row[0] == category_name:
                return row.iter
        
        # Crear nueva categoría
        return self.file_store.append(None, [category_name, ""])

    def _load_plugin_configs(self, server_path):
        """Carga archivos de configuración de plugins"""
        plugins_path = os.path.join(server_path, "plugins")
        if not os.path.exists(plugins_path):
            return
        
        try:
            # Buscar archivos YAML/YML en la carpeta plugins
            for item in os.listdir(plugins_path):
                item_path = os.path.join(plugins_path, item)
                
                if os.path.isdir(item_path):
                    # Es una carpeta de plugin, buscar config.yml dentro
                    self._scan_plugin_directory(item_path, item)
                elif item.endswith(('.yml', '.yaml')) and os.path.isfile(item_path):
                    # Es un archivo YAML directo en plugins/
                    category_iter = self._find_or_create_category("Plugin Configs")
                    self.file_store.append(category_iter, [item, item_path])
        
        except PermissionError:
            self.console_manager.log_to_console("Warning: Permission denied accessing plugins directory.\n")
        except Exception as e:
            self.console_manager.log_to_console(f"Error loading plugin configs: {e}\n")

    def _scan_plugin_directory(self, plugin_dir, plugin_name):
        """Escanea un directorio de plugin en busca de archivos de configuración"""
        try:
            for item in os.listdir(plugin_dir):
                item_path = os.path.join(plugin_dir, item)
                
                if os.path.isfile(item_path) and item.endswith(('.yml', '.yaml')):
                    # Crear categoría específica para este plugin
                    category_name = f"{plugin_name} Config"
                    category_iter = self._find_or_create_category(category_name)
                    
                    # Añadir archivo de configuración
                    display_name = f"{item}"
                    self.file_store.append(category_iter, [display_name, item_path])
                
                elif os.path.isdir(item_path) and item in ['config', 'configurations', 'settings']:
                    # Buscar recursivamente en subcarpetas comunes de configuración
                    self._scan_config_subdirectory(item_path, plugin_name, item)
        
        except PermissionError:
            pass  # Ignorar errores de permisos
        except Exception as e:
            self.console_manager.log_to_console(f"Error scanning plugin directory {plugin_name}: {e}\n")

    def _scan_config_subdirectory(self, config_dir, plugin_name, subdir_name):
        """Escanea subdirectorios de configuración de plugins"""
        try:
            for item in os.listdir(config_dir):
                item_path = os.path.join(config_dir, item)
                
                if os.path.isfile(item_path) and item.endswith(('.yml', '.yaml')):
                    category_name = f"{plugin_name} Config"
                    category_iter = self._find_or_create_category(category_name)
                    
                    # Incluir el subdirectorio en el nombre para claridad
                    display_name = f"{subdir_name}/{item}"
                    self.file_store.append(category_iter, [display_name, item_path])
        
        except Exception:
            pass  # Ignorar errores silenciosamente

    def _clear_file_list(self):
        """Limpia la lista de archivos"""
        self.file_store.clear()
        self._clear_editor()

    def _clear_editor(self):
        """Limpia el editor de configuración"""
        self.current_file = None
        self.config_data = {}
        self.widgets = {}
        self.file_info_label.set_markup("<i>Select a configuration file to edit</i>")
        self.save_button.set_sensitive(False)
        
        # Limpiar container
        for child in self.config_container.get_children():
            self.config_container.remove(child)

    def _on_file_selected(self, selection):
        """Maneja la selección de un archivo"""
        model, treeiter = selection.get_selected()
        if treeiter is None:
            return
            
        file_path = model[treeiter][1]
        if not file_path:  # Es una categoría
            return
            
        self._load_config_file(file_path)

    def _load_config_file(self, file_path):
        """Carga un archivo de configuración"""
        try:
            self.current_file = file_path
            filename = os.path.basename(file_path)
            self.file_info_label.set_markup(f"<b>Editing:</b> {filename}")
            
            # Limpiar editor anterior
            for child in self.config_container.get_children():
                self.config_container.remove(child)
            self.widgets = {}
            
            if file_path.endswith('.yml') or file_path.endswith('.yaml'):
                self._load_yaml_file(file_path)
            elif file_path.endswith('.properties'):
                self._load_properties_file(file_path)
            else:
                self._show_unsupported_file_message()
                
            self.save_button.set_sensitive(True)
            self.unsaved_changes = False
            
        except Exception as e:
            self.console_manager.log_to_console(f"Error loading config file {filename}: {e}\n")
            self._show_error_message(str(e))

    def _load_yaml_file(self, file_path):
        """Carga un archivo YAML"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraer comentarios
        comments = self._extract_yaml_comments(content)
        
        # Cargar datos YAML
        try:
            self.config_data = yaml.safe_load(content) or {}
        except yaml.YAMLError as e:
            raise Exception(f"Invalid YAML format: {e}")
        
        # Crear widgets para cada configuración
        self._create_yaml_widgets(self.config_data, comments)

    def _load_properties_file(self, file_path):
        """Carga un archivo .properties"""
        properties = {}
        comments = {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        current_comment = ""
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('#'):
                current_comment += line[1:].strip() + "\n"
            elif '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                properties[key] = value
                if current_comment:
                    comments[key] = current_comment.strip()
                    current_comment = ""
            elif line == "":
                current_comment = ""
        
        self.config_data = properties
        self._create_properties_widgets(properties, comments)

    def _extract_yaml_comments(self, content: str) -> Dict[str, str]:
        """Extrae comentarios de un archivo YAML"""
        comments = {}
        lines = content.split('\n')
        current_comment = ""
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#'):
                # Limpiar el comentario
                comment_text = stripped[1:].strip()
                if comment_text:  # Solo añadir comentarios no vacíos
                    current_comment += comment_text + "\n"
            elif ':' in stripped and not stripped.startswith('#'):
                # Buscar el key
                key_part = stripped.split(':')[0].strip()
                if current_comment:
                    comments[key_part] = current_comment.strip()
                    current_comment = ""
            elif stripped == "":
                # Línea vacía puede separar comentarios
                if current_comment and not current_comment.endswith("\n\n"):
                    current_comment += "\n"
        
        return comments

    def _create_yaml_widgets(self, data: Dict[str, Any], comments: Dict[str, str], prefix: str = ""):
        """Crea widgets para datos YAML"""
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Crear sección expandible para objetos anidados
                self._create_section_header(key, comments.get(key, ""))
                self._create_yaml_widgets(value, comments, full_key)
            else:
                # Crear widget para valor simple
                self._create_config_widget(key, value, comments.get(key, ""), full_key)

    def _create_properties_widgets(self, properties: Dict[str, str], comments: Dict[str, str]):
        """Crea widgets para archivo .properties"""
        for key, value in properties.items():
            self._create_config_widget(key, value, comments.get(key, ""), key)

    def _create_section_header(self, title: str, help_text: str):
        """Crea un header de sección"""
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        label = Gtk.Label()
        label.set_markup(f"<b>{title.replace('_', ' ').title()}</b>")
        label.set_halign(Gtk.Align.START)
        header_box.pack_start(label, False, False, 0)
        
        if help_text:
            help_button = Gtk.Button.new_from_icon_name("help-about", Gtk.IconSize.BUTTON)
            help_button.set_tooltip_text(help_text)
            help_button.set_relief(Gtk.ReliefStyle.NONE)
            header_box.pack_start(help_button, False, False, 0)
        
        self.config_container.pack_start(header_box, False, False, 0)

    def _create_config_widget(self, key: str, value: Any, help_text: str, full_key: str):
        """Crea un widget para un elemento de configuración"""
        container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        container.set_margin_left(12)
        
        # Header con nombre y ayuda
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # Label del campo
        label = Gtk.Label()
        label.set_markup(f"<b>{key.replace('_', ' ').replace('-', ' ').title()}:</b>")
        label.set_halign(Gtk.Align.START)
        header_box.pack_start(label, False, False, 0)
        
        # Botón de ayuda si hay comentario
        if help_text:
            help_button = Gtk.Button.new_from_icon_name("help-about", Gtk.IconSize.BUTTON)
            help_button.set_tooltip_text(help_text)
            help_button.set_relief(Gtk.ReliefStyle.NONE)
            header_box.pack_start(help_button, False, False, 0)
        
        container.pack_start(header_box, False, False, 0)
        
        # Widget de entrada según el tipo de valor
        widget = self._create_input_widget(value, full_key)
        container.pack_start(widget, False, False, 0)
        
        # Texto de ayuda debajo si existe
        if help_text:
            help_label = Gtk.Label()
            help_label.set_markup(f"<small><i>{help_text}</i></small>")
            help_label.set_halign(Gtk.Align.START)
            help_label.set_line_wrap(True)
            help_label.set_max_width_chars(80)
            container.pack_start(help_label, False, False, 0)
        
        self.config_container.pack_start(container, False, False, 0)
        self.config_container.show_all()

    def _create_input_widget(self, value: Any, key: str):
        """Crea el widget de entrada apropiado según el tipo de valor"""
        if isinstance(value, bool):
            widget = Gtk.Switch()
            widget.set_active(value)
            widget.connect("notify::active", self._on_value_changed, key)
        elif isinstance(value, int):
            widget = Gtk.SpinButton()
            # Rango más amplio para plugins que pueden usar valores grandes
            adjustment = Gtk.Adjustment(value, -2147483648, 2147483647, 1, 10, 0)
            widget.set_adjustment(adjustment)
            widget.connect("value-changed", self._on_value_changed, key)
        elif isinstance(value, float):
            widget = Gtk.SpinButton()
            adjustment = Gtk.Adjustment(value, -999999.0, 999999.0, 0.1, 1.0, 0)
            widget.set_adjustment(adjustment)
            widget.set_digits(3)  # Más precisión para plugins
            widget.connect("value-changed", self._on_value_changed, key)
        elif isinstance(value, list):
            # Para listas, mostrar como texto editable (formato YAML)
            widget = Gtk.TextView()
            widget.set_size_request(-1, 100)
            buffer = widget.get_buffer()
            
            # Convertir lista a formato YAML legible
            if all(isinstance(item, str) for item in value):
                # Lista de strings
                list_text = "\n".join(f"- {item}" for item in value)
            else:
                # Lista mixta, usar representación YAML
                import yaml
                list_text = yaml.dump(value, default_flow_style=False).strip()
            
            buffer.set_text(list_text)
            buffer.connect("changed", self._on_text_buffer_changed, key)
            
            # Envolver en ScrolledWindow
            scrolled = Gtk.ScrolledWindow()
            scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            scrolled.add(widget)
            self.widgets[key] = widget  # Guardar referencia al TextView, no al ScrolledWindow
            return scrolled
        else:
            # String o unknown - mejorado para detectar valores especiales
            widget = Gtk.Entry()
            str_value = str(value)
            widget.set_text(str_value)
            
            # Si es una cadena muy larga, usar TextView en su lugar
            if len(str_value) > 100:
                text_widget = Gtk.TextView()
                text_widget.set_size_request(-1, 80)
                buffer = text_widget.get_buffer()
                buffer.set_text(str_value)
                buffer.connect("changed", self._on_text_buffer_changed, key)
                
                scrolled = Gtk.ScrolledWindow()
                scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
                scrolled.add(text_widget)
                self.widgets[key] = text_widget
                return scrolled
            else:
                widget.connect("changed", self._on_value_changed, key)
        
        self.widgets[key] = widget
        return widget

    def _on_text_buffer_changed(self, buffer, key):
        """Maneja cambios en TextBuffer"""
        self.unsaved_changes = True
        # Cambiar el título para indicar cambios no guardados
        current_text = self.file_info_label.get_text()
        if not current_text.endswith(" *"):
            self.file_info_label.set_markup(f"{current_text} <b>*</b>")

    def _on_value_changed(self, widget, *args):
        """Maneja cambios en los valores de configuración"""
        self.unsaved_changes = True
        # Cambiar el título para indicar cambios no guardados
        current_text = self.file_info_label.get_text()
        if not current_text.endswith(" *"):
            self.file_info_label.set_markup(f"{current_text} <b>*</b>")

    def _on_refresh_files(self, widget):
        """Refresca la lista de archivos"""
        if self.selected_server:
            self._load_config_files()
            self.console_manager.log_to_console("Configuration files refreshed.\n")

    def _on_save_config(self, widget):
        """Guarda la configuración actual"""
        if not self.current_file:
            return
        
        try:
            # Recopilar valores de los widgets
            updated_data = self._collect_widget_values()
            
            # Guardar archivo
            if self.current_file.endswith('.yml') or self.current_file.endswith('.yaml'):
                self._save_yaml_file(updated_data)
            elif self.current_file.endswith('.properties'):
                self._save_properties_file(updated_data)
            
            self.unsaved_changes = False
            filename = os.path.basename(self.current_file)
            self.file_info_label.set_markup(f"<b>Editing:</b> {filename}")
            self.console_manager.log_to_console(f"Configuration file {filename} saved successfully.\n")
            
        except Exception as e:
            self.console_manager.log_to_console(f"Error saving configuration: {e}\n")

    def _collect_widget_values(self) -> Dict[str, Any]:
        """Recopila los valores de todos los widgets"""
        updated_data = self.config_data.copy()
        
        for key, widget in self.widgets.items():
            if isinstance(widget, Gtk.Switch):
                value = widget.get_active()
            elif isinstance(widget, Gtk.SpinButton):
                if widget.get_digits() > 0:
                    value = widget.get_value()
                else:
                    value = int(widget.get_value())
            elif isinstance(widget, Gtk.Entry):
                text = widget.get_text()
                # Intentar convertir a tipo original si es posible
                original_value = self._get_nested_value(self.config_data, key)
                value = self._convert_text_to_type(text, type(original_value))
            elif isinstance(widget, Gtk.TextView):
                # Para TextViews (listas y textos largos)
                buffer = widget.get_buffer()
                start = buffer.get_start_iter()
                end = buffer.get_end_iter()
                text = buffer.get_text(start, end, False)
                
                # Determinar si es una lista o texto
                original_value = self._get_nested_value(self.config_data, key)
                if isinstance(original_value, list):
                    value = self._parse_list_from_text(text)
                else:
                    value = text
            else:
                continue
            
            # Actualizar el valor en la estructura de datos
            self._set_nested_value(updated_data, key, value)
        
        return updated_data

    def _get_nested_value(self, data: Dict[str, Any], key: str):
        """Obtiene un valor de una estructura anidada usando notación de puntos"""
        if '.' in key:
            keys = key.split('.')
            current = data
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return None
            return current
        else:
            return data.get(key)

    def _convert_text_to_type(self, text: str, target_type):
        """Convierte texto al tipo objetivo"""
        try:
            if target_type == int:
                return int(text)
            elif target_type == float:
                return float(text)
            elif target_type == bool:
                return text.lower() in ('true', '1', 'yes', 'on')
            else:
                return text
        except (ValueError, TypeError):
            return text

    def _parse_list_from_text(self, text: str):
        """Parsea una lista desde texto en formato YAML"""
        try:
            import yaml
            # Intentar parsear como YAML
            parsed = yaml.safe_load(text)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, str):
                # Si es un string, dividir por líneas y limpiar
                lines = [line.strip() for line in text.split('\n')]
                return [line.lstrip('- ') for line in lines if line and not line.startswith('#')]
            else:
                return [text]
        except yaml.YAMLError:
            # Si falla el parseo YAML, dividir por líneas
            lines = [line.strip() for line in text.split('\n')]
            return [line.lstrip('- ') for line in lines if line and not line.startswith('#')]

    def _set_nested_value(self, data: Dict[str, Any], key: str, value: Any):
        """Establece un valor en una estructura anidada usando notación de puntos"""
        if '.' in key:
            keys = key.split('.')
            current = data
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value
        else:
            data[key] = value

    def _save_yaml_file(self, data: Dict[str, Any]):
        """Guarda un archivo YAML"""
        with open(self.current_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)

    def _save_properties_file(self, data: Dict[str, Any]):
        """Guarda un archivo .properties"""
        with open(self.current_file, 'w', encoding='utf-8') as f:
            for key, value in data.items():
                f.write(f"{key}={value}\n")

    def _show_unsupported_file_message(self):
        """Muestra mensaje para archivos no soportados"""
        label = Gtk.Label()
        label.set_markup("<i>This file type is not supported for visual editing.</i>")
        self.config_container.pack_start(label, True, True, 0)
        self.config_container.show_all()

    def _show_error_message(self, error: str):
        """Muestra mensaje de error"""
        label = Gtk.Label()
        label.set_markup(f"<span color='red'><b>Error:</b> {error}</span>")
        label.set_line_wrap(True)
        self.config_container.pack_start(label, True, True, 0)
        self.config_container.show_all()
