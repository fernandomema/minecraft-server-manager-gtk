"""
Diálogo para añadir un nuevo servidor
"""
import gi
import os
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

_ = gettext.gettext

from utils.file_utils import get_jar_files_in_directory


class AddServerDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title=_("Add New Minecraft Server"), parent=parent, flags=0)

        # Replace deprecated stock buttons with custom ones
        cancel_button = Gtk.Button(label=_("Cancel"))
        cancel_button.set_image(Gtk.Image.new_from_icon_name("window-close", Gtk.IconSize.BUTTON))
        cancel_button.set_always_show_image(True)
        cancel_button.connect("clicked", lambda btn: self.response(Gtk.ResponseType.CANCEL))
        self.add_action_widget(cancel_button, Gtk.ResponseType.CANCEL)

        add_button = Gtk.Button(label=_("Add"))
        add_button.set_image(Gtk.Image.new_from_icon_name("list-add", Gtk.IconSize.BUTTON))
        add_button.set_always_show_image(True)
        add_button.connect("clicked", lambda btn: self.response(Gtk.ResponseType.OK))
        self.add_action_widget(add_button, Gtk.ResponseType.OK)

        self.set_default_size(400, 250)
        self._setup_ui()

    def _setup_ui(self):
        """Configura la interfaz de usuario"""
        box = self.get_content_area()
        box.set_spacing(10)

        # Server Name
        name_label = Gtk.Label(label=_("Server Name:"))
        self.name_entry = Gtk.Entry()
        box.pack_start(name_label, False, False, 0)
        box.pack_start(self.name_entry, False, False, 0)

        # Server Directory
        dir_label = Gtk.Label(label=_("Server Directory:"))
        self.dir_entry = Gtk.Entry()
        self.dir_entry.connect("changed", self._on_dir_entry_changed)
        
        self.dir_button = Gtk.Button(label=_("Browse..."))
        self.dir_button.connect("clicked", self._on_dir_button_clicked)

        dir_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        dir_hbox.pack_start(self.dir_entry, True, True, 0)
        dir_hbox.pack_start(self.dir_button, False, False, 0)

        box.pack_start(dir_label, False, False, 0)
        box.pack_start(dir_hbox, False, False, 0)

        # Server JAR File (Dropdown)
        jar_label = Gtk.Label(label=_("Server JAR File:"))
        self.jar_combobox = Gtk.ComboBoxText()
        self.jar_combobox.append_text(_("DOWNLOAD_LATER"))
        self.jar_combobox.set_active(0)

        box.pack_start(jar_label, False, False, 0)
        box.pack_start(self.jar_combobox, False, False, 0)

        self.show_all()

    def _on_dir_button_clicked(self, widget):
        """Maneja el clic en el botón de seleccionar directorio"""
        dialog = Gtk.FileChooserDialog(
            title=_("Select Server Directory"),
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
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
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.dir_entry.set_text(dialog.get_filename())
        dialog.destroy()

    def _on_dir_entry_changed(self, entry):
        """Maneja cambios en el campo de directorio"""
        self.jar_combobox.remove_all()
        self.jar_combobox.append_text(_("DOWNLOAD_LATER"))
        self.jar_combobox.set_active(0)

        server_dir = entry.get_text()
        if os.path.isdir(server_dir):
            jar_files = get_jar_files_in_directory(server_dir)
            for jar_file in jar_files:
                self.jar_combobox.append_text(jar_file)

    def get_server_details(self) -> dict:
        """Obtiene los detalles del servidor del diálogo"""
        return {
            "name": self.name_entry.get_text(),
            "path": self.dir_entry.get_text(),
            "jar": self.jar_combobox.get_active_text()
        }
