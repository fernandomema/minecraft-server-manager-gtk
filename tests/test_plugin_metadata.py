import json
import sys
from pathlib import Path
import types

sys.path.append(str(Path(__file__).resolve().parents[1]))

gi = types.ModuleType("gi")
repository = types.ModuleType("repository")
gi.repository = repository
repository.GLib = types.SimpleNamespace(idle_add=lambda *args, **kwargs: None)
sys.modules.setdefault("gi", gi)
sys.modules.setdefault("gi.repository", repository)
sys.modules.setdefault("gi.repository.GLib", repository.GLib)

from controllers.plugin_controller import PluginController
from models.plugin import Plugin


def test_add_plugin_metadata_capitalizes_install_method(tmp_path):
    controller = PluginController()
    server_path = str(tmp_path)
    controller._add_plugin_metadata(server_path, "TestPlugin", "modrinth", "123")
    data = json.loads((tmp_path / ".plugin_metadata.json").read_text())
    assert data["TestPlugin"]["install_method"] == "Modrinth"


def test_get_install_method_display():
    plugin = Plugin(name="TestPlugin", install_method="Modrinth")
    assert plugin.get_install_method_display() == "🌐 Modrinth"
