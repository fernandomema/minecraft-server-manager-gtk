import json
import sys
import zipfile
from pathlib import Path
import types

sys.path.append(str(Path(__file__).resolve().parents[1]))

# Stub GLib for tests
gi = types.ModuleType("gi")
repository = types.ModuleType("repository")
gi.repository = repository
repository.GLib = types.SimpleNamespace(idle_add=lambda *args, **kwargs: None)
sys.modules.setdefault("gi", gi)
sys.modules.setdefault("gi.repository", repository)
sys.modules.setdefault("gi.repository.GLib", repository.GLib)

from controllers.plugin_controller import PluginController


def _create_jar_with_plugin_yml(tmp_path):
    jar_path = tmp_path / "testplugin.jar"
    with zipfile.ZipFile(jar_path, "w") as jar:
        jar.writestr("plugin.yml", "name: TestPlugin\nversion: 1.2.3\n")
    return jar_path


def _create_jar_with_fabric_json(tmp_path):
    jar_path = tmp_path / "testmod.jar"
    meta = {"id": "testmod", "version": "0.4.0"}
    with zipfile.ZipFile(jar_path, "w") as jar:
        jar.writestr("fabric.mod.json", json.dumps(meta))
    return jar_path


def test_extract_version_from_plugin(tmp_path):
    controller = PluginController()
    jar_path = _create_jar_with_plugin_yml(tmp_path)
    assert controller._extract_version_from_jar(str(jar_path)) == "1.2.3"


def test_extract_version_from_fabric_mod(tmp_path):
    controller = PluginController()
    jar_path = _create_jar_with_fabric_json(tmp_path)
    assert controller._extract_version_from_jar(str(jar_path)) == "0.4.0"
