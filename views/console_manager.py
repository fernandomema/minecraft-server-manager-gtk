"""
Console Manager for the Minecraft Server Manager
Handles console output, logging, and auto-scroll functionality
"""
import gi
import re
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

_ = gettext.gettext


class ConsoleManager:
    """Manages console functionality for the server manager"""
    
    def __init__(self):
        self.console_buffer = None
        self.console_view = None
        self.console_scrolled_window = None
        self.console_adjustment = None
        self.text_tags = {}
        self.auto_scroll_enabled = True  # Auto-scroll siempre activo por defecto
        
    def setup_console_view(self, container):
        """Configura la vista de consola"""
        self.console_buffer = Gtk.TextBuffer()
        self._setup_text_tags()
        
        self.console_view = Gtk.TextView(buffer=self.console_buffer)
        self.console_view.set_editable(False)
        self.console_view.set_cursor_visible(False)

        self.console_scrolled_window = Gtk.ScrolledWindow()
        self.console_scrolled_window.set_hexpand(True)
        self.console_scrolled_window.set_vexpand(True)
        self.console_scrolled_window.add(self.console_view)
        container.pack_start(self.console_scrolled_window, True, True, 0)
        
        # Configurar auto-scroll
        self.console_adjustment = self.console_scrolled_window.get_vadjustment()
        
        # Configurar estilo DESPUÉS de crear todos los widgets
        self._setup_console_style()
        
        return {
            'console_buffer': self.console_buffer,
            'console_view': self.console_view,
            'console_scrolled_window': self.console_scrolled_window
        }

    def _setup_text_tags(self):
        """Configura los tags de texto para colorización"""
        # Usar colores optimizados para fondo oscuro desde el inicio
        self.text_tags = {
            'info': self.console_buffer.create_tag(
                "info", 
                foreground="#66BB6A"  # Verde claro para información del sistema
            ),
            'error': self.console_buffer.create_tag(
                "error", 
                foreground="#EF5350",  # Rojo claro para errores
                weight=700  # Bold
            ),
            'warning': self.console_buffer.create_tag(
                "warning", 
                foreground="#FFA726"  # Naranja claro para advertencias
            ),
            'server_info': self.console_buffer.create_tag(
                "server_info", 
                foreground="#42A5F5"  # Azul claro para información del servidor
            ),
            'server_done': self.console_buffer.create_tag(
                "server_done", 
                foreground="#9CCC65",  # Verde lima para tareas completadas
                weight=700
            ),
            'player_join': self.console_buffer.create_tag(
                "player_join", 
                foreground="#66BB6A"  # Verde para jugadores que se unen
            ),
            'player_leave': self.console_buffer.create_tag(
                "player_leave", 
                foreground="#FFAB40"  # Naranja para jugadores que se van
            ),
            'chat': self.console_buffer.create_tag(
                "chat", 
                foreground="#AB47BC"  # Púrpura para chat
            ),
            'debug': self.console_buffer.create_tag(
                "debug", 
                foreground="#BDBDBD"  # Gris claro para debug
            ),
            'timestamp': self.console_buffer.create_tag(
                "timestamp", 
                foreground="#78909C"  # Gris azulado para timestamps
            ),
            'stderr': self.console_buffer.create_tag(
                "stderr", 
                foreground="#FF7043"  # Rojo naranja para stderr
            ),
            'default': self.console_buffer.create_tag(
                "default", 
                foreground="#E8EAF6"  # Blanco azulado para texto normal
            )
        }

    def _classify_message(self, message: str):
        """Clasifica el mensaje según su contenido y devuelve el tag apropiado"""
        # Limpiar el mensaje para análisis
        clean_message = message.strip()
        clean_lower = clean_message.lower()
        
        # Si el mensaje ya tiene prefijo [STDERR], usar ese tag
        if message.startswith('[STDERR]'):
            return 'stderr'
        
        # Patterns para diferentes tipos de mensajes de Minecraft
        
        # Errores (alta prioridad)
        error_patterns = [
            r'\[ERROR\]', r'ERROR:', r'Exception', r'failed', r'couldn\'t', 
            r'unable to', r'not found', r'invalid', r'fatal', r'crash',
            r'stacktrace', r'caused by:', r'at \w+\.'
        ]
        
        # Advertencias
        warning_patterns = [
            r'\[WARN\]', r'WARNING:', r'warn:', r'deprecated', r'outdated',
            r'ambiguous', r'legacy'
        ]
        
        # Información del servidor (logs estructurados)
        server_info_patterns = [
            r'\[Server thread/INFO\]', r'\[main/INFO\]', r'\[Worker-Main',
            r'Loading properties', r'Default game type:', r'Generating keypair',
            r'Starting minecraft server', r'Loading libraries', r'Environment:',
            r'Loaded \d+ recipes', r'Loaded \d+ advancements'
        ]
        
        # Servidor completando tareas importantes
        server_done_patterns = [
            r'Done \([^)]+\)! For help', r'Time elapsed:', r'Preparing spawn area:',
            r'Spawn area successfully loaded', r'Server startup complete'
        ]
        
        # Jugadores uniéndose
        player_join_patterns = [
            r'(\w+) joined the game', r'(\w+)\[\/[\d.]+:\d+\] logged in',
            r'UUID of player \w+ is', r'(\w+) has made the advancement'
        ]
        
        # Jugadores saliendo
        player_leave_patterns = [
            r'(\w+) left the game', r'(\w+) lost connection',
            r'Disconnecting (\w+)', r'(\w+) has disconnected'
        ]
        
        # Chat del juego
        chat_patterns = [
            r'<\w+>', r'\[Server\]', r'\[CONSOLE\]'
        ]
        
        # Debug/Trace
        debug_patterns = [
            r'\[DEBUG\]', r'debug:', r'trace:', r'\[TRACE\]'
        ]
        
        # Información importante del servidor (performance, world saving, etc.)
        important_server_patterns = [
            r'Saving the game', r'Saved the game', r'Automatic saving',
            r'ThreadedAnvilChunkStorage', r'Preparing start region',
            r'Timings Reset'
        ]
        
        # Verificar patrones en orden de prioridad
        pattern_groups = [
            ('error', error_patterns),
            ('warning', warning_patterns),
            ('server_done', server_done_patterns),
            ('player_join', player_join_patterns),
            ('player_leave', player_leave_patterns),
            ('chat', chat_patterns),
            ('debug', debug_patterns),
            ('server_info', important_server_patterns + server_info_patterns)
        ]
        
        for tag_name, pattern_list in pattern_groups:
            for pattern in pattern_list:
                if re.search(pattern, clean_message, re.IGNORECASE):
                    return tag_name
        
        # Verificar si es información del sistema (nuestras propias líneas)
        system_indicators = [
            'loaded', 'saved', 'added server', 'starting server', 'server',
            'stopped', 'configuration', 'download', 'eula', 'pid:'
        ]
        
        for indicator in system_indicators:
            if indicator in clean_lower and not any(p in clean_message for p in ['[', ']', 'thread']):
                return 'info'
        
        return 'default'

    def _setup_console_style(self):
        """Configura el estilo de la consola para mejor contraste"""
        # Aplicar fondo oscuro y texto claro por defecto
        css_provider = Gtk.CssProvider()
        css = """
        textview {
            background-color: #1e1e1e;
            color: #ffffff;
            font-family: 'Consolas', 'DejaVu Sans Mono', 'Liberation Mono', monospace;
            font-size: 10pt;
            padding: 8px;
        }
        
        textview text {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        
        .console-view {
            background-color: #1e1e1e;
            color: #ffffff;
        }
        
        scrolledwindow {
            background-color: #1e1e1e;
        }
        """
        css_provider.load_from_data(css.encode())
        
        # Aplicar el CSS al contexto del TextView
        context = self.console_view.get_style_context()
        context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        context.add_class("console-view")
        
        # También aplicar al ScrolledWindow si existe
        if self.console_scrolled_window:
            scrolled_context = self.console_scrolled_window.get_style_context()
            scrolled_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        # Configurar colores de fondo directamente en el widget
        color = Gdk.RGBA()
        color.parse("#1e1e1e")
        self.console_view.override_background_color(Gtk.StateFlags.NORMAL, color)
        
        # Color del texto por defecto
        text_color = Gdk.RGBA()
        text_color.parse("#ffffff")
        self.console_view.override_color(Gtk.StateFlags.NORMAL, text_color)

    def _update_tags_for_dark_theme(self):
        """Actualiza los colores de los tags para que funcionen bien con fondo oscuro"""
        # Recrear tags con colores optimizados para fondo oscuro
        dark_colors = {
            'info': "#66BB6A",        # Verde claro para información del sistema
            'error': "#EF5350",       # Rojo claro para errores
            'warning': "#FFA726",     # Naranja claro para advertencias
            'server_info': "#42A5F5", # Azul claro para información del servidor
            'server_done': "#9CCC65", # Verde lima para tareas completadas
            'player_join': "#66BB6A", # Verde para jugadores que se unen
            'player_leave': "#FFAB40", # Naranja para jugadores que se van
            'chat': "#AB47BC",        # Púrpura para chat
            'debug': "#BDBDBD",       # Gris claro para debug
            'timestamp': "#78909C",   # Gris azulado para timestamps
            'stderr': "#FF7043",      # Rojo naranja para stderr
            'default': "#E8EAF6"      # Blanco azulado para texto normal
        }
        
        # Actualizar tags existentes
        for tag_name, color in dark_colors.items():
            if tag_name in self.text_tags:
                self.text_tags[tag_name].set_property("foreground", color)

    def log_to_console_with_timestamp(self, message: str, add_timestamp: bool = True):
        """Añade un mensaje a la consola con timestamp opcional y colorización"""
        if add_timestamp and not message.startswith('[') and not message.startswith('    '):
            # Añadir timestamp para mensajes del sistema
            import datetime
            timestamp = datetime.datetime.now().strftime("[%H:%M:%S] ")
            
            # Insertar timestamp con su propio color
            if self.console_buffer and self.console_adjustment:
                end_iter = self.console_buffer.get_end_iter()
                self.console_buffer.insert_with_tags(
                    end_iter, timestamp, self.text_tags['timestamp']
                )
            
            # Luego insertar el mensaje normal (sin timestamp adicional)
            self.log_to_console(message)
        else:
            # Insertar mensaje sin timestamp
            self.log_to_console(message)

    def log_to_console(self, message: str):
        """Añade un mensaje a la consola con auto-scroll y colorización"""
        if not self.console_buffer or not self.console_adjustment:
            return
            
        # Clasificar el mensaje y obtener el tag apropiado
        tag_name = self._classify_message(message)
        tag = self.text_tags.get(tag_name, self.text_tags['default'])

        # Obtener la posición final del buffer
        end_iter = self.console_buffer.get_end_iter()
        
        # Insertar texto con el tag correspondiente
        self.console_buffer.insert_with_tags(end_iter, message, tag)

        # Auto-scroll basado en la configuración
        if self.auto_scroll_enabled:
            self._scroll_to_bottom()
        else:
            # Auto-scroll inteligente: solo si el usuario está al final
            if self.is_at_bottom():
                self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        """Hace scroll al final de la consola"""
        if not self.console_adjustment:
            return
            
        # Usar GLib.idle_add para asegurar que el scroll se haga después de que el texto se haya renderizado
        from gi.repository import GLib
        GLib.idle_add(self._do_scroll_to_bottom)
    
    def _do_scroll_to_bottom(self):
        """Ejecuta el scroll al final en el hilo principal"""
        if self.console_adjustment:
            # Obtener el máximo valor de scroll
            upper = self.console_adjustment.get_upper()
            page_size = self.console_adjustment.get_page_size()
            # Hacer scroll al final
            self.console_adjustment.set_value(max(0, upper - page_size))
        return False  # No repetir la operación

    def scroll_to_bottom(self):
        """Método público para hacer scroll al final de la consola"""
        self._scroll_to_bottom()

    def is_at_bottom(self):
        """Verifica si el scroll está en la parte inferior"""
        if not self.console_adjustment:
            return True
            
        current = self.console_adjustment.get_value()
        page_size = self.console_adjustment.get_page_size()
        upper = self.console_adjustment.get_upper()
        
        # Considerar que estamos "al final" si estamos dentro de los últimos 10 pixels
        return current + page_size >= upper - 10

    def log_to_console_smart_scroll(self, message: str):
        """Añade un mensaje con auto-scroll inteligente (solo si el usuario está al final)"""
        if not self.console_buffer or not self.console_adjustment:
            return
            
        # Verificar si estamos al final antes de añadir el mensaje
        was_at_bottom = self.is_at_bottom()
        
        # Clasificar el mensaje y obtener el tag apropiado
        tag_name = self._classify_message(message)
        tag = self.text_tags.get(tag_name, self.text_tags['default'])

        # Obtener la posición final del buffer
        end_iter = self.console_buffer.get_end_iter()
        
        # Insertar texto con el tag correspondiente
        self.console_buffer.insert_with_tags(end_iter, message, tag)

        # Solo hacer auto-scroll si estábamos al final
        if was_at_bottom:
            self._scroll_to_bottom()

    def set_auto_scroll(self, enabled: bool):
        """Habilita o deshabilita el auto-scroll automático"""
        self.auto_scroll_enabled = enabled

    def toggle_auto_scroll(self):
        """Alterna el estado del auto-scroll"""
        self.auto_scroll_enabled = not self.auto_scroll_enabled
        return self.auto_scroll_enabled

    def get_auto_scroll_status(self):
        """Obtiene el estado actual del auto-scroll"""
        return self.auto_scroll_enabled

    def clear_console(self):
        """Limpia el contenido de la consola"""
        if self.console_buffer:
            self.console_buffer.set_text("")
            
    def get_console_text(self):
        """Obtiene todo el texto de la consola"""
        if self.console_buffer:
            start = self.console_buffer.get_start_iter()
            end = self.console_buffer.get_end_iter()
            return self.console_buffer.get_text(start, end, False)
        return ""
