"""
About dialog for Minecraft Server Manager
"""
import gi
import os
import sys
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf

_ = gettext.gettext


class AboutDialog:
    """Shows the About dialog"""

    APP_ID = "io.github.fernandomema.minecraft-server-manager-gtk"
    APP_VERSION = "1.0.0"
    APP_WEBSITE = "https://github.com/fernandomema/minecraft-server-manager-gtk"

    @staticmethod
    def show(parent_window):
        """Create and display the About dialog."""
        dialog = Gtk.AboutDialog(transient_for=parent_window, modal=True)

        dialog.set_program_name(_("Minecraft Server Manager"))
        dialog.set_version(AboutDialog.APP_VERSION)
        dialog.set_comments(
            _("A GTK application to manage Minecraft servers with ease.")
        )
        dialog.set_website(AboutDialog.APP_WEBSITE)
        dialog.set_website_label(_("GitHub Repository"))
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_copyright("© 2025-2026 Fernando Merino")
        dialog.set_authors(["Fernando Merino"])

        # Try to load the application icon
        icon_path = AboutDialog._find_icon()
        if icon_path:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    icon_path, 128, 128, True
                )
                dialog.set_logo(pixbuf)
            except Exception:
                dialog.set_logo_icon_name("applications-games")
        else:
            dialog.set_logo_icon_name("applications-games")

        dialog.run()
        dialog.destroy()

    @staticmethod
    def _find_icon():
        """Locate the application icon file."""
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        candidates = [
            os.path.join(base, f"{AboutDialog.APP_ID}.svg"),
            os.path.join(base, f"{AboutDialog.APP_ID}-128.png"),
            os.path.join(base, f"{AboutDialog.APP_ID}-64.png"),
            os.path.join(base, f"{AboutDialog.APP_ID}-48.png"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return None
