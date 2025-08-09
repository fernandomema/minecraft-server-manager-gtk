"""
Server Management Page for the Minecraft Server Manager
Contains all UI and logic related to server configuration and management
"""
import gi
import os
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

_ = gettext.gettext

from models.server import MinecraftServer
from views.add_server_dialog import AddServerDialog
from views.download_server_dialog import DownloadServerDialog
from views.eula_dialog import EulaDialog


class ServerManagementPage:
    """Handles server management UI and events"""
    
    def __init__(self, parent_window, server_controller, download_controller, console_manager):
        self.parent_window = parent_window
        self.server_controller = server_controller
        self.download_controller = download_controller
        self.console_manager = console_manager
        self.selected_server = None
        
        # UI Components
        self.server_info_label = None
        self.server_name_entry = None
        self.server_path_entry = None
        self.server_jar_combo = None
        self.download_jar_button = None
        self.save_config_button = None
        self.refresh_jars_button = None
        self.unlink_server_button = None
        self.delete_server_button = None

    def create_page(self):
        """Crea la página de gestión de servidores"""
        server_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        server_page.set_margin_left(12)
        server_page.set_margin_right(12)
        server_page.set_margin_top(12)
        server_page.set_margin_bottom(12)

        # Título de la página
        title_label = Gtk.Label()
        title_label.set_markup(_("<b>Server Management</b>"))
        title_label.set_halign(Gtk.Align.START)
        title_label.set_margin_bottom(12)
        server_page.pack_start(title_label, False, False, 0)

        # Sección de configuración del servidor
        self._setup_server_configuration_section(server_page)

        # Consola (sección principal)
        console_widgets = self.console_manager.setup_console_view(server_page)
        
        return server_page

    def _setup_server_configuration_section(self, container):
        """Configura la sección de configuración del servidor"""
        # Frame para la configuración del servidor
        config_frame = Gtk.Frame(label=_("Server Configuration"))
        container.pack_start(config_frame, False, False, 0)
        
        config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        config_box.set_margin_left(12)
        config_box.set_margin_right(12)
        config_box.set_margin_top(12)
        config_box.set_margin_bottom(12)
        config_frame.add(config_box)
        
        # Información del servidor seleccionado
        self.server_info_label = Gtk.Label()
        self.server_info_label.set_markup(_("<i>Select a server from the title bar to configure</i>"))
        self.server_info_label.set_halign(Gtk.Align.START)
        config_box.pack_start(self.server_info_label, False, False, 0)
        
        # Grid para los campos de configuración
        config_grid = Gtk.Grid()
        config_grid.set_column_spacing(12)
        config_grid.set_row_spacing(8)
        config_box.pack_start(config_grid, False, False, 0)
        
        # Server Name
        name_label = Gtk.Label(label=_("Server Name:"))
        name_label.set_halign(Gtk.Align.END)
        self.server_name_entry = Gtk.Entry()
        self.server_name_entry.set_sensitive(False)
        self.server_name_entry.connect("changed", self._on_server_name_changed)
        
        config_grid.attach(name_label, 0, 0, 1, 1)
        config_grid.attach(self.server_name_entry, 1, 0, 2, 1)
        
        # Server Path
        path_label = Gtk.Label(label=_("Server Path:"))
        path_label.set_halign(Gtk.Align.END)
        self.server_path_entry = Gtk.Entry()
        self.server_path_entry.set_sensitive(False)
        self.server_path_entry.set_editable(False)  # Solo lectura
        
        config_grid.attach(path_label, 0, 1, 1, 1)
        config_grid.attach(self.server_path_entry, 1, 1, 2, 1)
        
        # JAR File
        jar_label = Gtk.Label(label=_("JAR File:"))
        jar_label.set_halign(Gtk.Align.END)
        self.server_jar_combo = Gtk.ComboBoxText()
        self.server_jar_combo.set_sensitive(False)
        self.server_jar_combo.connect("changed", self._on_server_jar_changed)
        
        config_grid.attach(jar_label, 0, 2, 1, 1)
        config_grid.attach(self.server_jar_combo, 1, 2, 1, 1)
        
        # Botón para descargar JAR
        self.download_jar_button = Gtk.Button(label=_("Download JAR"))
        self.download_jar_button.set_sensitive(False)
        self.download_jar_button.connect("clicked", self._on_download_jar_clicked)
        config_grid.attach(self.download_jar_button, 2, 2, 1, 1)
        
        # Botones de acción
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        action_box.set_halign(Gtk.Align.CENTER)
        config_box.pack_start(action_box, False, False, 12)
        
        self.save_config_button = Gtk.Button(label=_("Save Configuration"))
        self.save_config_button.set_sensitive(False)
        self.save_config_button.connect("clicked", self._on_save_config_clicked)
        action_box.pack_start(self.save_config_button, False, False, 0)
        
        self.refresh_jars_button = Gtk.Button(label=_("Refresh JARs"))
        self.refresh_jars_button.set_sensitive(False)
        self.refresh_jars_button.connect("clicked", self._on_refresh_jars_clicked)
        action_box.pack_start(self.refresh_jars_button, False, False, 0)
        
        # Separador
        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        action_box.pack_start(separator, False, False, 6)
        
        # Botones de gestión del servidor
        self.unlink_server_button = Gtk.Button(label=_("Unlink Server"))
        self.unlink_server_button.set_sensitive(False)
        self.unlink_server_button.get_style_context().add_class("warning-action")
        self.unlink_server_button.connect("clicked", self._on_unlink_server_clicked)
        action_box.pack_start(self.unlink_server_button, False, False, 0)
        
        self.delete_server_button = Gtk.Button(label=_("Delete Server"))
        self.delete_server_button.set_sensitive(False)
        self.delete_server_button.get_style_context().add_class("destructive-action")
        self.delete_server_button.connect("clicked", self._on_delete_server_clicked)
        action_box.pack_start(self.delete_server_button, False, False, 0)

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
            self.console_manager.log_to_console("Please select a server first.\n")
            return

        dialog = DownloadServerDialog(self.parent_window)
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
            
            # Notificar al parent window para actualizar la lista
            if hasattr(self.parent_window, '_refresh_server_list'):
                self.parent_window._refresh_server_list()
                self.parent_window._select_server_by_name(new_name)
            
            self.console_manager.log_to_console(f"Server name changed from '{old_name}' to '{new_name}'\n")

        # Actualizar JAR seleccionado
        selected_jar = self.server_jar_combo.get_active_text()
        if selected_jar and selected_jar != self.selected_server.jar:
            old_jar = self.selected_server.jar
            self.server_controller.update_server_jar(self.selected_server, selected_jar)
            self.console_manager.log_to_console(f"Server JAR changed from '{old_jar}' to '{selected_jar}'\n")

        # Guardar cambios
        if self.server_controller.save_servers():
            self.console_manager.log_to_console("Server configuration saved successfully.\n")
            self.save_config_button.set_sensitive(False)
            # Notificar al parent window para actualizar botones
            if hasattr(self.parent_window, '_update_header_buttons'):
                self.parent_window._update_header_buttons()
        else:
            self.console_manager.log_to_console("Error saving server configuration.\n")

    def _on_refresh_jars_clicked(self, widget):
        """Maneja el clic en refrescar JARs"""
        if self.selected_server:
            self._update_jar_list()
            self.console_manager.log_to_console("JAR list refreshed.\n")

    def _on_unlink_server_clicked(self, widget):
        """Maneja el clic en desvincular servidor"""
        if not self.selected_server:
            return

        # Diálogo de confirmación
        dialog = Gtk.MessageDialog(
            parent=self.parent_window,
            flags=Gtk.DialogFlags.MODAL,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Unlink Server '{name}'?").format(name=self.selected_server.name)
        )
        dialog.format_secondary_text(
            _(
                "This will remove the server from the manager but will NOT delete the server files from your disk. The server data will remain intact."
            )
        )

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            server_name = self.selected_server.name
            if self._unlink_server(self.selected_server):
                self.console_manager.log_to_console(f"Server '{server_name}' has been unlinked from the manager.\n")

    def _on_delete_server_clicked(self, widget):
        """Maneja el clic en eliminar servidor"""
        if not self.selected_server:
            return

        # Diálogo de confirmación más estricto
        dialog = Gtk.MessageDialog(
            parent=self.parent_window,
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
                parent=self.parent_window,
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
                    self.console_manager.log_to_console(f"Server '{server_name}' and all its files have been permanently deleted from '{server_path}'.\n")
                else:
                    self.console_manager.log_to_console(f"Error: Could not delete server '{server_name}'. Check permissions and try again.\n")
            else:
                self.console_manager.log_to_console("Server deletion cancelled - name confirmation failed.\n")

    def show_add_server_dialog(self):
        """Muestra el diálogo para añadir un nuevo servidor"""
        dialog = AddServerDialog(self.parent_window)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            details = dialog.get_server_details()
            if self.server_controller.add_server(
                details["name"], details["path"], details["jar"]
            ):
                # Notificar al parent window
                if hasattr(self.parent_window, '_refresh_server_list'):
                    self.parent_window._refresh_server_list()
                # Seleccionar el nuevo servidor
                new_server = self.server_controller.find_server_by_name(details["name"])
                if new_server and hasattr(self.parent_window, '_select_server_by_name'):
                    self.parent_window._select_server_by_name(details["name"])
        
        dialog.destroy()

    def start_server(self):
        """Inicia el servidor seleccionado"""
        if not self.selected_server:
            return

        # Verificar EULA si es necesario
        if not self._check_and_handle_eula():
            return

        self.server_controller.start_server(self.selected_server)
        # Notificar al parent window para actualizar botones
        if hasattr(self.parent_window, '_update_header_buttons'):
            self.parent_window._update_header_buttons()

    def stop_server(self):
        """Detiene el servidor seleccionado"""
        if self.selected_server:
            self.server_controller.stop_server(self.selected_server)

    def kill_server(self):
        """Mata el servidor seleccionado"""
        if self.selected_server:
            self.server_controller.kill_server(self.selected_server)

    def _unlink_server(self, server: MinecraftServer) -> bool:
        """Desvincula un servidor de la gestión (no elimina archivos)"""
        try:
            # Usar el método del controlador
            success = self.server_controller.remove_server(server)
            
            if success:
                # Notificar al parent window
                if hasattr(self.parent_window, '_refresh_server_list'):
                    self.parent_window._refresh_server_list()
                
                # Limpiar selección actual
                self.selected_server = None
                if hasattr(self.parent_window, '_update_header_buttons'):
                    self.parent_window._update_header_buttons()
                self.clear_server_configuration()
            
            return success
            
        except Exception as e:
            self.console_manager.log_to_console(f"Error unlinking server: {e}\n")
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
                self.console_manager.log_to_console(f"Deleted server directory: {server.path}\n")
            
            # Usar el método del controlador para eliminar de la lista
            success = self.server_controller.remove_server(server)
            
            if success:
                # Notificar al parent window
                if hasattr(self.parent_window, '_refresh_server_list'):
                    self.parent_window._refresh_server_list()
                
                # Limpiar selección actual
                self.selected_server = None
                if hasattr(self.parent_window, '_update_header_buttons'):
                    self.parent_window._update_header_buttons()
                self.clear_server_configuration()
            
            return success
            
        except Exception as e:
            self.console_manager.log_to_console(f"Error deleting server: {e}\n")
            return False

    def select_server(self, server: MinecraftServer):
        """Selecciona un servidor"""
        self.selected_server = server
        self.update_server_configuration(server)

    def update_server_configuration(self, server: MinecraftServer):
        """Actualiza los campos de configuración del servidor"""
        if not self.server_name_entry:
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

    def clear_server_configuration(self):
        """Limpia los campos de configuración cuando no hay servidor seleccionado"""
        if not self.server_name_entry:
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

    def _update_jar_list(self):
        """Actualiza la lista de JARs disponibles"""
        if not self.selected_server or not self.server_jar_combo:
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

    def _check_and_handle_eula(self) -> bool:
        """Verifica y maneja el EULA si es necesario"""
        if not self.selected_server:
            return False

        eula_path = f"{self.selected_server.path}/eula.txt"
        if not self.server_controller._check_eula(self.selected_server):
            dialog = EulaDialog(self.parent_window, self.selected_server.name)
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
            if hasattr(self.parent_window, '_refresh_server_list'):
                self.parent_window._refresh_server_list()
            if hasattr(self.parent_window, '_update_header_buttons'):
                self.parent_window._update_header_buttons()

        self.download_controller.download_paper_jar(
            version, 
            self.selected_server.path, 
            on_download_success
        )
