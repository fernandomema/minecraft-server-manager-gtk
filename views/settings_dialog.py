"""
Settings dialog for Minecraft Server Manager
"""
import gi
import os
import gettext
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

_ = gettext.gettext

from utils.constants import USER_DATA_DIR
from utils.file_utils import load_json_file, save_json_file

SETTINGS_FILE = os.path.join(USER_DATA_DIR, "settings.json")

# Default settings
DEFAULT_SETTINGS = {
    "default_java_memory": "1024M",
    "auto_accept_eula": False,
    "show_console_timestamps": True,
    "confirm_server_stop": True,
    "confirm_server_kill": True,
    "theme": "system",   # system | light | dark
}


def load_settings() -> dict:
    """Load application settings, returning defaults for missing keys."""
    try:
        data = load_json_file(SETTINGS_FILE)
        if isinstance(data, dict):
            merged = dict(DEFAULT_SETTINGS)
            merged.update(data)
            return merged
    except Exception:
        pass
    return dict(DEFAULT_SETTINGS)


def save_settings(settings: dict) -> bool:
    """Persist application settings to disk."""
    return save_json_file(SETTINGS_FILE, settings)


class SettingsDialog(Gtk.Dialog):
    """Application settings dialog."""

    def __init__(self, parent_window):
        Gtk.Dialog.__init__(
            self,
            title=_("Settings"),
            transient_for=parent_window,
            modal=True,
            destroy_with_parent=True,
        )
        self.set_default_size(480, -1)
        self.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        save_btn = self.add_button(_("Save"), Gtk.ResponseType.OK)
        save_btn.get_style_context().add_class("suggested-action")

        self._settings = load_settings()
        self._build_ui()

    # ── UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        content = self.get_content_area()
        content.set_spacing(12)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.set_margin_top(12)
        content.set_margin_bottom(6)

        # ─ General section ────────────────────────────────────────────
        general_label = Gtk.Label()
        general_label.set_markup("<b>" + _("General") + "</b>")
        general_label.set_halign(Gtk.Align.START)
        content.pack_start(general_label, False, False, 0)

        general_grid = Gtk.Grid()
        general_grid.set_row_spacing(8)
        general_grid.set_column_spacing(12)
        general_grid.set_margin_start(12)
        content.pack_start(general_grid, False, False, 0)

        # Theme
        row = 0
        theme_label = Gtk.Label(label=_("Theme:"))
        theme_label.set_halign(Gtk.Align.END)
        general_grid.attach(theme_label, 0, row, 1, 1)

        self._theme_combo = Gtk.ComboBoxText()
        for val, text in [
            ("system", _("System")),
            ("light", _("Light")),
            ("dark", _("Dark")),
        ]:
            self._theme_combo.append(val, text)
        self._theme_combo.set_active_id(self._settings.get("theme", "system"))
        general_grid.attach(self._theme_combo, 1, row, 1, 1)

        # ─ Server section ─────────────────────────────────────────────
        server_label = Gtk.Label()
        server_label.set_markup("<b>" + _("Server") + "</b>")
        server_label.set_halign(Gtk.Align.START)
        server_label.set_margin_top(8)
        content.pack_start(server_label, False, False, 0)

        server_grid = Gtk.Grid()
        server_grid.set_row_spacing(8)
        server_grid.set_column_spacing(12)
        server_grid.set_margin_start(12)
        content.pack_start(server_grid, False, False, 0)

        # Default Java memory
        row = 0
        mem_label = Gtk.Label(label=_("Default Java memory:"))
        mem_label.set_halign(Gtk.Align.END)
        server_grid.attach(mem_label, 0, row, 1, 1)

        self._memory_entry = Gtk.Entry()
        self._memory_entry.set_text(self._settings.get("default_java_memory", "1024M"))
        self._memory_entry.set_tooltip_text(
            _("Memory allocation for the JVM (e.g. 1024M, 2G)")
        )
        server_grid.attach(self._memory_entry, 1, row, 1, 1)

        # Auto-accept EULA
        row += 1
        self._eula_switch = Gtk.Switch()
        self._eula_switch.set_active(self._settings.get("auto_accept_eula", False))
        self._eula_switch.set_halign(Gtk.Align.START)
        eula_label = Gtk.Label(label=_("Auto-accept EULA:"))
        eula_label.set_halign(Gtk.Align.END)
        server_grid.attach(eula_label, 0, row, 1, 1)
        server_grid.attach(self._eula_switch, 1, row, 1, 1)

        # ─ Console section ────────────────────────────────────────────
        console_label = Gtk.Label()
        console_label.set_markup("<b>" + _("Console") + "</b>")
        console_label.set_halign(Gtk.Align.START)
        console_label.set_margin_top(8)
        content.pack_start(console_label, False, False, 0)

        console_grid = Gtk.Grid()
        console_grid.set_row_spacing(8)
        console_grid.set_column_spacing(12)
        console_grid.set_margin_start(12)
        content.pack_start(console_grid, False, False, 0)

        # Show timestamps
        row = 0
        self._timestamps_switch = Gtk.Switch()
        self._timestamps_switch.set_active(
            self._settings.get("show_console_timestamps", True)
        )
        self._timestamps_switch.set_halign(Gtk.Align.START)
        ts_label = Gtk.Label(label=_("Show timestamps:"))
        ts_label.set_halign(Gtk.Align.END)
        console_grid.attach(ts_label, 0, row, 1, 1)
        console_grid.attach(self._timestamps_switch, 1, row, 1, 1)

        # ─ Confirmations section ──────────────────────────────────────
        confirm_label = Gtk.Label()
        confirm_label.set_markup("<b>" + _("Confirmations") + "</b>")
        confirm_label.set_halign(Gtk.Align.START)
        confirm_label.set_margin_top(8)
        content.pack_start(confirm_label, False, False, 0)

        confirm_grid = Gtk.Grid()
        confirm_grid.set_row_spacing(8)
        confirm_grid.set_column_spacing(12)
        confirm_grid.set_margin_start(12)
        content.pack_start(confirm_grid, False, False, 0)

        # Confirm stop
        row = 0
        self._confirm_stop_switch = Gtk.Switch()
        self._confirm_stop_switch.set_active(
            self._settings.get("confirm_server_stop", True)
        )
        self._confirm_stop_switch.set_halign(Gtk.Align.START)
        stop_label = Gtk.Label(label=_("Confirm server stop:"))
        stop_label.set_halign(Gtk.Align.END)
        confirm_grid.attach(stop_label, 0, row, 1, 1)
        confirm_grid.attach(self._confirm_stop_switch, 1, row, 1, 1)

        # Confirm kill
        row += 1
        self._confirm_kill_switch = Gtk.Switch()
        self._confirm_kill_switch.set_active(
            self._settings.get("confirm_server_kill", True)
        )
        self._confirm_kill_switch.set_halign(Gtk.Align.START)
        kill_label = Gtk.Label(label=_("Confirm server kill:"))
        kill_label.set_halign(Gtk.Align.END)
        confirm_grid.attach(kill_label, 0, row, 1, 1)
        confirm_grid.attach(self._confirm_kill_switch, 1, row, 1, 1)

        content.show_all()

    # ── Read values back ───────────────────────────────────────────────

    def get_settings(self) -> dict:
        """Return the current values from the dialog widgets."""
        return {
            "theme": self._theme_combo.get_active_id() or "system",
            "default_java_memory": self._memory_entry.get_text().strip() or "1024M",
            "auto_accept_eula": self._eula_switch.get_active(),
            "show_console_timestamps": self._timestamps_switch.get_active(),
            "confirm_server_stop": self._confirm_stop_switch.get_active(),
            "confirm_server_kill": self._confirm_kill_switch.get_active(),
        }

    # ── Convenience class method ───────────────────────────────────────

    @classmethod
    def run_dialog(cls, parent_window) -> bool:
        """Show the dialog and save settings if the user clicks Save.
        Returns True if settings were saved."""
        dialog = cls(parent_window)
        response = dialog.run()
        saved = False
        if response == Gtk.ResponseType.OK:
            new_settings = dialog.get_settings()
            save_settings(new_settings)
            saved = True
        dialog.destroy()
        return saved
