# Minecraft Server Manager GTK

Una aplicación con interfaz gráfica GTK para gestionar servidores de Minecraft.

## Estructura del Proyecto

El proyecto ha sido refactorizado siguiendo el patrón MVC (Model-View-Controller):

```
minecraft-server-manager-gtk/
├── main.py                     # Archivo original (respaldo)
├── main_new.py                 # Nuevo punto de entrada
├── servers.json               # Configuración de servidores
├── models/                    # Modelos de datos
│   ├── __init__.py
│   ├── server.py             # Modelo de servidor
│   └── plugin.py             # Modelo de plugin/mod
├── views/                     # Interfaces de usuario
│   ├── __init__.py
│   ├── main_window.py        # Ventana principal
│   ├── add_server_dialog.py  # Diálogo añadir servidor
│   ├── download_server_dialog.py # Diálogo descarga
│   └── eula_dialog.py        # Diálogo EULA
├── controllers/               # Lógica de negocio
│   ├── __init__.py
│   ├── server_controller.py  # Controlador de servidores
│   ├── download_controller.py # Controlador de descargas
│   └── plugin_controller.py  # Controlador de plugins
├── utils/                     # Utilidades
│   ├── __init__.py
│   ├── constants.py          # Constantes
│   └── file_utils.py         # Utilidades de archivos
└── servers/                   # Directorios de servidores
    └── test/                  # Servidor de ejemplo
```

## Beneficios de la Refactorización

### 1. **Separación de Responsabilidades**
- **Models**: Representan los datos (Servidor, Plugin)
- **Views**: Manejan la interfaz de usuario
- **Controllers**: Contienen la lógica de negocio

### 2. **Reutilización de Código**
- Los controladores pueden ser reutilizados en diferentes vistas
- Las acciones están centralizadas y son fáciles de mantener

### 3. **Mantenibilidad**
- Cada archivo tiene una responsabilidad específica
- Es más fácil encontrar y modificar funcionalidades
- Mejor organización del código

### 4. **Escalabilidad**
- Fácil añadir nuevas funcionalidades
- Estructura preparada para crecimiento

### 5. **Testabilidad**
- Los controladores pueden ser probados independientemente
- Separación clara entre lógica y presentación

## Componentes Principales

### Models (models/)
- `server.py`: Representa un servidor de Minecraft
- `plugin.py`: Representa un plugin o mod

### Controllers (controllers/)
- `server_controller.py`: Gestiona servidores (iniciar, parar, configurar)
- `download_controller.py`: Maneja descargas de JARs
- `plugin_controller.py`: Gestiona plugins y mods

### Views (views/)
- `main_window.py`: Ventana principal refactorizada
- `add_server_dialog.py`: Diálogo para añadir servidores
- `download_server_dialog.py`: Diálogo para descargar JARs
- `eula_dialog.py`: Diálogo para aceptar EULA

### Utils (utils/)
- `constants.py`: Constantes de la aplicación
- `file_utils.py`: Utilidades para manejo de archivos

## Uso

### Ejecutar la Aplicación
```bash
python3 main_new.py
```

### Migración desde el Código Original
El archivo `main.py` original se mantiene como respaldo. La nueva estructura es completamente compatible y ofrece las mismas funcionalidades.

## Características

- **Gestión de Servidores**: Añadir, iniciar, parar servidores
- **Descarga de JARs**: Descarga automática de PaperMC
- **Gestión de Plugins**: Administrar plugins y mods
- **Consola Integrada**: Ver salida de servidores en tiempo real
- **Búsqueda Online**: Buscar plugins en Modrinth

## Próximas Mejoras

Con esta nueva estructura es más fácil implementar:
- Sistema de configuración avanzado
- Soporte para más tipos de servidores
- Descarga e instalación automática de plugins
- Sistema de backups
- Monitoreo de rendimiento
- API REST para control remoto

## Dependencias

- Python 3.6+
- PyGObject (Gtk 3.0)
- Java (para ejecutar servidores)

La refactorización mantiene todas las funcionalidades existentes mientras proporciona una base sólida para futuras mejoras.
