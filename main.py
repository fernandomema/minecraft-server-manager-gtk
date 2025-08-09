#!/usr/bin/env python3
"""
Archivo principal de la aplicación Minecraft Server Manager
Punto de entrada simplificado que utiliza la arquitectura MVC
"""
import os
import sys
import locale
import gettext
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from views.main_window import MinecraftServerManager

# Configuración de internacionalización
def setup_i18n():
    """Configura la internacionalización de la aplicación"""
    # Obtener el directorio base de la aplicación
    if getattr(sys, 'frozen', False):
        # Si está empaquetado (AppImage, etc.)
        app_dir = os.path.dirname(sys.executable)
    else:
        # Si está ejecutándose desde código fuente
        app_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Directorio de traducciones
    locale_dir = os.path.join(app_dir, 'locale')
    
    # Configurar locale del sistema
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        # Fallback si no se puede configurar el locale del sistema
        try:
            locale.setlocale(locale.LC_ALL, 'C.UTF-8')
        except locale.Error:
            pass
    
    # Obtener el idioma del sistema
    lang = locale.getdefaultlocale()[0]
    if lang:
        # Extraer solo el código de idioma (ej: 'es' de 'es_ES')
        lang_code = lang.split('_')[0]
        os.environ['LANGUAGE'] = lang_code
    
    # Configurar gettext
    try:
        # Usar bindtextdomain para especificar la ubicación de las traducciones
        gettext.bindtextdomain('messages', locale_dir)
        gettext.textdomain('messages')
        
        # Instalar la función _ globalmente
        gettext.install('messages', locale_dir)
        
        print(f"I18n configured: locale_dir={locale_dir}, language={os.environ.get('LANGUAGE', 'default')}")
    except Exception as e:
        print(f"Warning: Could not load translations: {e}")
        # Usar gettext dummy si falla
        import builtins
        builtins.__dict__['_'] = lambda x: x


def main():
    """Función principal de la aplicación"""
    try:
        # Configurar internacionalización antes de crear la aplicación
        setup_i18n()
        
        app = MinecraftServerManager()
        app.show_all()
        Gtk.main()
    except Exception as e:
        print(f"Error starting application: {e}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())
