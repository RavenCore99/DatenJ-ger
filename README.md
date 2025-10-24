                                                DATENJÄGER | SISTEMA DE GESTIÓN DOCUMENTAL |

                                                        
                                                        Sistema de Base de Datos con Almacenamiento en PDF
Descripción General
Este proyecto es un sistema de base de datos complejo diseñado para gestionar datos estructurados utilizando SQLite y generar reportes en formato PDF a partir de los datos almacenados. Es ideal para aplicaciones que requieren persistencia de datos y generación de reportes en PDF.
Funcionalidades

Gestión de Datos: Utiliza SQLite para crear y administrar una base de datos relacional que almacena registros (por ejemplo, con campos como ID, nombre y descripción).
Almacenamiento de Datos: Soporta operaciones CRUD (Crear, Leer, Actualizar, Eliminar) para gestionar registros.
Generación de PDFs: Convierte los registros de la base de datos en reportes PDF formateados usando la librería ReportLab.
Diseño Modular: Organizado en capas (gestión de base de datos, procesamiento de datos y exportación a PDF) para facilitar escalabilidad y mantenimiento.
Interfaz de Línea de Comandos: Incluye un CLI simple para interactuar con la base de datos y generar PDFs.

Requisitos

Python 3.8 o superior
SQLite (incluido con Python)
Librería ReportLab para generación de PDFs

Instalación

Clona el repositorio:git clone <https://github.com/RavenCore99/DatenJ-ger.git>
Rama V.1
O simplemente accediendo directamente desde el navegador al repositorio, busca la carpeta Setup en
la Rama "Lauch-Test"

1. Si clonaste el repositorio. Puedes ejecutar directamente el Software en la carpeta RUN, lo puedes abrir dando doble clic
2. Tambien puedes compilarlo de dos formas mas [O usando el terminal (requiere Python, librerias y complementos)] [Usar editor de codigo (requiere Python, scripts, librerias)]

La ruta facil

Descargar directamente en el apartado "Release" en GitHub






Funciones dentro del codigo

Inicializar la Base de Datos:Ejecuta el script principal para crear la base de datos SQLite y las tablas:
python main.py init

Esto crea un archivo database.db con una tabla de ejemplo llamada registros.

Agregar Registros:Inserta datos en la base de datos:
python main.py agregar "Nombre Ejemplo" "Descripción Ejemplo"

Reemplaza "Nombre Ejemplo" y "Descripción Ejemplo" con datos reales.

Consultar Registros:Recupera todos los registros:
python main.py listar


Generar Reporte PDF:Exporta los registros a un archivo PDF:
python main.py exportar_pdf salida.pdf

Esto genera un archivo PDF llamado salida.pdf con todos los registros.

Actualizar o Eliminar Registros:Actualiza un registro por ID:
python main.py actualizar <id> "Nuevo Nombre" "Nueva Descripción"

Elimina un registro por ID:
python main.py eliminar <id>



Estructura del Proyecto

main.py: Punto de entrada para el CLI y lógica principal.
database.py: Maneja las operaciones de la base de datos SQLite (crear, insertar, actualizar, eliminar, consultar).
pdf_generator.py: Gestiona la creación de archivos PDF usando ReportLab.
database.db: Archivo de la base de datos SQLite (se crea al inicializar).
salida.pdf: Archivo PDF generado (se crea al exportar).

Dependencias

Python: Versión 3.8+ para la funcionalidad principal.
SQLite: Incluido con Python para la gestión ligera de la base de datos.
ReportLab: Versión 3.6+ para la generación de archivos PDF.
Instalar con: pip install reportlab




Licencia
Licencia MIT. Consulta el archivo LICENSE para más detalles.

Version
Alpha V.1 Launch Test 