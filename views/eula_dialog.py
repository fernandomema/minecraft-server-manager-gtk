"""
Diálogo para mostrar acuerdo EULA
"""
import gi
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

_ = gettext.gettext


class EulaDialog(Gtk.MessageDialog):
    def __init__(self, parent, server_name: str):
        super().__init__(
            parent=parent,
            flags=0,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.YES_NO,
            text=_("Minecraft EULA Agreement Required")
        )
        
        self.format_secondary_text(
            _(
                "To run the Minecraft server '{server_name}', you must agree to the "
                "Minecraft End User License Agreement (EULA). "
                "You can read the EULA at https://account.mojang.com/documents/minecraft_eula. "
                "Do you accept the EULA?"
            ).format(server_name=server_name)
        )
    
    def run_and_get_response(self) -> bool:
        """Ejecuta el diálogo y retorna True si se acepta el EULA"""
        response = self.run()
        self.destroy()
        return response == Gtk.ResponseType.YES
