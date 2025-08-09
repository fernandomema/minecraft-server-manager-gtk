"""
Diálogo para descargar servidores
"""
import gi
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

_ = gettext.gettext

from controllers.download_controller import DownloadController


class DownloadServerDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title=_("Download Minecraft Server JAR"), parent=parent, flags=0)

        cancel_button = Gtk.Button(label=_("Cancel"))
        cancel_button.set_image(Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.BUTTON))
        cancel_button.set_always_show_image(True)
        cancel_button.connect("clicked", lambda btn: self.response(Gtk.ResponseType.CANCEL))
        self.add_action_widget(cancel_button, Gtk.ResponseType.CANCEL)

        download_button = Gtk.Button(label=_("Download"))
        download_button.set_image(Gtk.Image.new_from_icon_name("go-down", Gtk.IconSize.BUTTON))
        download_button.set_always_show_image(True)
        download_button.connect("clicked", lambda btn: self.response(Gtk.ResponseType.OK))
        self.add_action_widget(download_button, Gtk.ResponseType.OK)

        self.set_default_size(400, 200)
        self.download_controller = DownloadController()
        self.download_controller.set_download_callback(self._on_status_update)

        self._setup_ui()
        self._load_initial_data()

    def _setup_ui(self):
        """Configura la interfaz de usuario"""
        box = self.get_content_area()
        box.set_spacing(10)

        # Server Type
        type_label = Gtk.Label(label=_("Server Type:"))
        self.type_combobox = Gtk.ComboBoxText()
        self.type_combobox.append_text(_("Paper"))
        self.type_combobox.set_active(0)
        self.type_combobox.connect("changed", self._on_server_type_changed)

        box.pack_start(type_label, False, False, 0)
        box.pack_start(self.type_combobox, False, False, 0)

        # Version
        version_label = Gtk.Label(label=_("Version:"))
        self.version_combobox = Gtk.ComboBoxText()
        box.pack_start(version_label, False, False, 0)
        box.pack_start(self.version_combobox, False, False, 0)

        # Status
        self.status_label = Gtk.Label(label="")
        box.pack_start(self.status_label, False, False, 0)

        self.show_all()

    def _load_initial_data(self):
        """Carga los datos iniciales"""
        self._on_server_type_changed(self.type_combobox)

    def _on_server_type_changed(self, combobox):
        """Maneja cambios en el tipo de servidor"""
        selected_type = combobox.get_active_text()
        self.version_combobox.remove_all()
        self.status_label.set_text(_("Fetching versions..."))

        if selected_type == _("Paper"):
            self.download_controller.get_paper_versions_async(self._on_versions_loaded)
        else:
            self.status_label.set_text(_("Unsupported server type."))

    def _on_versions_loaded(self, versions):
        """Maneja cuando se cargan las versiones"""
        for version in versions:
            self.version_combobox.append_text(version)
        
        if versions:
            self.version_combobox.set_active(0)
            self.status_label.set_text(_("Versions loaded."))
        else:
            self.status_label.set_text(_("No versions found."))

    def _on_status_update(self, message):
        """Actualiza el estado en la etiqueta"""
        self.status_label.set_text(message.strip())

    def get_download_details(self) -> dict:
        """Obtiene los detalles de descarga"""
        return {
            "type": self.type_combobox.get_active_text(),
            "version": self.version_combobox.get_active_text()
        }
