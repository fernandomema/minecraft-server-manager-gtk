"""Utilidades para manejo de archivos y configuraciones"""
import json
import logging
import os
from typing import Any, Dict, List, Union


JSONData = Union[Dict[str, Any], List[Any]]


def load_json_file(file_path: str) -> JSONData:
    """Carga un archivo JSON y retorna los datos"""
    if not os.path.exists(file_path):
        logging.error("JSON file not found: %s", file_path)
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error("Error loading JSON file %s: %s", file_path, e)
        raise


def save_json_file(file_path: str, data: JSONData) -> bool:
    """Guarda datos en un archivo JSON"""
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logging.error("Error saving JSON file %s: %s", file_path, e)
        raise


def ensure_directory_exists(directory_path: str) -> bool:
    """Asegura que un directorio existe, lo crea si no existe"""
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Error creating directory {directory_path}: {e}")
        return False


def get_jar_files_in_directory(directory_path: str) -> List[str]:
    """Obtiene todos los archivos .jar en un directorio"""
    jar_files = []
    if os.path.isdir(directory_path):
        for filename in os.listdir(directory_path):
            if filename.endswith(".jar"):
                jar_files.append(filename)
    return jar_files


def get_plugins_and_mods(server_path: str) -> List[tuple]:
    """Obtiene lista de plugins y mods en un servidor"""
    items = []
    
    # Buscar en directorio plugins
    plugins_dir = os.path.join(server_path, "plugins")
    if os.path.isdir(plugins_dir):
        for filename in os.listdir(plugins_dir):
            if filename.endswith(".jar"):
                full_path = os.path.join(plugins_dir, filename)
                items.append((filename, full_path))
    
    # Buscar en directorio mods
    mods_dir = os.path.join(server_path, "mods")
    if os.path.isdir(mods_dir):
        for filename in os.listdir(mods_dir):
            if filename.endswith(".jar"):
                full_path = os.path.join(mods_dir, filename)
                items.append((filename, full_path))
    
    return items
