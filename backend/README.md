# Capa backend de DatenJäger

Documentación de la extracción de lógica de negocio fuera de la interfaz
CustomTkinter (Sprint 2 — `SCRUM-12` a `SCRUM-19`).

## Por qué existe esta carpeta

Antes de la extracción, cada panel mezclaba SQL, cifrado y renderizado en
el mismo método: `pdf_manager.py`, `personas.py` y `audit.py` construían
ventanas y ejecutaban operaciones de negocio en el mismo cuerpo. Esta
carpeta concentra esa lógica en servicios invocables **sin Tkinter**, de
modo que el frontend Electron/React pueda consumirla sin depender de la
interfaz actual.

## Estructura

```text
backend/
├── errors.py                # excepciones tipadas de la capa
├── state.py                 # AppState / SesionUsuario (sesión, tema, config)
├── commands.py              # ComandosDatenJager: punto de entrada único
├── services/
│   ├── documentos.py        # CRUD de PDFs + cifrado/descifrado
│   ├── personas.py          # CRUD de titulares
│   ├── auditoria.py         # registro, consulta, limpieza, log del sistema
│   └── reportes.py          # métricas del dashboard y exportación PDF/CSV
└── README.md

chatbot.py (raíz)            # servicio del asistente; ya estaba libre de UI
```

## Reglas de la capa

1. **Nada de interfaz.** Ningún módulo de `backend/` importa
   `customtkinter`, `tkinter`, `ui_components` ni los paneles. Hay una
   prueba que lo verifica en un subproceso sin `DISPLAY`.
2. **Dependencias explícitas.** Los servicios reciben
   `(conn, cursor, ...)` y el usuario como argumento; nunca leen estado
   desde una clase de UI.
3. **Errores tipados.** Los servicios levantan `BackendError` y sus
   derivadas (`NoAutenticadoError`, `NoEncontradoError`,
   `DatosInvalidosError`, `ConflictoError`). La UI traduce el error a una
   notificación; el servicio nunca muestra mensajes.
4. **Auditoría best-effort.** `registrar_evento` devuelve `False` si falla
   pero no interrumpe la operación de negocio que lo originó.
5. **Sin cambios de esquema ni de cifrado.** Se conserva SQLite con WAL y
   AES-256-GCM con la clave derivada del nombre de usuario.

## Firmas de los servicios

Todos los servicios comparten la firma `(conn, cursor, ...)`:

| Servicio | Operaciones |
| --- | --- |
| `services.documentos` | `listar_documentos`, `obtener_documento`, `contar_documentos`, `crear_documento`, `crear_documento_desde_archivo`, `actualizar_documento`, `eliminar_documento`, `leer_documento`, `exportar_documento` |
| `services.personas` | `listar_personas`, `obtener_persona`, `contar_personas`, `crear_persona`, `actualizar_persona`, `eliminar_persona` |
| `services.auditoria` | `registrar_evento`, `listar_eventos`, `contar_eventos`, `limpiar_historial`, `construir_log_sistema` |
| `services.reportes` | `estadisticas`, `documentos_por_empresa`, `documentos_por_dia`, `datos_inventario`, `exportar_inventario` |

## Punto de entrada único

```python
from database import conectar_db
from backend.state import AppState
from backend.commands import ComandosDatenJager

conn, cursor = conectar_db()                     # o conectar_db("/ruta/otra.db")
state = AppState(conn=conn, cursor=cursor, db_lock=lock, config=config)
comandos = ComandosDatenJager(state)

comandos.iniciar_sesion(usuario_id=1, nombre="raven", session_key=clave)
comandos.listar_documentos()
comandos.agregar_documento("/ruta/afiliacion.pdf", descripcion="EPS",
                           cedula="1023", nombres="Ana Diaz", empresa="Minera Ubaté")
comandos.estadisticas_dashboard()
comandos.cerrar_sesion()
```

Todo comando de negocio verifica que exista sesión activa y levanta
`NoAutenticadoError` si no la hay. El acceso a la conexión SQLite se
serializa con `state.db_lock`.

## Alcance pendiente

La verificación de credenciales, el flujo 2FA, el cambio de contraseña y
el token de confianza siguen en `main.py`: forman parte del flujo de
autenticación y requieren aprobación explícita antes de moverse. El
catálogo está disponible en el código:

```python
ComandosDatenJager.operaciones_pendientes()
```

## Pruebas

```bash
python -m unittest discover -s tests -t . -v
```

46 pruebas sobre una base temporal con el esquema real (nunca tocan
`base_datos_pdfs.db`). Incluyen un caso que reintenta todo el backend en
un subproceso sin `DISPLAY` para garantizar que no dependa de la interfaz.