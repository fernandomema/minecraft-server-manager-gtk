#!/usr/bin/env python3
"""
Archivo principal de la aplicación Minecraft Server Manager
Punto de entrada simplificado que utiliza la arquitectura MVC
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from views.main_window import MinecraftServerManager


def main():
    """Función principal de la aplicación"""
    try:
        app = MinecraftServerManager()
        app.show_all()
        Gtk.main()
    except Exception as e:
        print(f"Error starting application: {e}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
