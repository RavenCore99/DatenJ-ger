# Decisión de motor de persistencia — `SCRUM-43`

> Jira: **SCRUM-43** «Evaluar persistencia de modelos y datos»
> (`datenjager`, `evaluacion`, `persistencia`).
> Fecha: 2026-10-01. Estado: **decidido**, sin cambio de motor.

## La pregunta

El anteproyecto dejó abierto si SQLite (con WAL, como hoy) sigue siendo
suficiente una vez el acceso a los datos pasa por el puente Python↔Electron en
producción, o si conviene otra alternativa. La decisión se pospone a propósito
hasta que la Fase 2 revele el patrón real de acceso concurrente.

## Qué se ha observado (el patrón real)

La Fase 2 y la Fase 3 ya están construidas y funcionando, así que el patrón de
acceso es un hecho, no una previsión:

| Hecho | Consecuencia |
| --- | --- |
| El servicio es **un solo proceso** (`python -m backend.server`), levantado por Electron. | No hay varios escritores: no hace falta coordinación entre procesos. |
| Dentro de ese proceso hay **una conexión y un cursor** compartidos (`AppState`), y toda operación pasa por `ComandosDatenJager._ejecutar`, que toma `AppState.db_lock`. | La concurrencia está serializada por un cerrojo en memoria; SQLite nunca ve dos escrituras a la vez desde la aplicación. |
| El renderer **no toca la base**: habla HTTP con el puente. | El número de clientes no multiplica conexiones a SQLite. |
| WAL está activo (`PRAGMA journal_mode=WAL`). | Las lecturas no bloquean a la escritura y viceversa; es lo que permite que la franja de telemetría consulte mientras alguien sube un documento. |
| El volumen es de **una pyme minera**: cientos o pocos miles de documentos, con los PDF cifrados en la propia base. | No hay presión de escala que justifique un motor cliente-servidor. |
| La base vive **en el equipo del usuario**, cifrada en reposo, y la instalación debe generarla en local (Fase 7). | Un motor con servidor exigiría un servicio extra en el instalador: más superficie, más fallos de arranque. |

## La decisión

**Se mantiene SQLite con WAL.** No se cambia de motor.

Los tres criterios que el anteproyecto pedía evaluar quedan respondidos:

1. **¿Sufre por la concurrencia del puente?** No. El puente no añade
   concurrentes: el proceso del servicio sigue siendo único y serializa con
   `db_lock`. El acceso concurrente real es *un renderer* haciendo una petición
   mientras la franja de telemetría hace otra lectura; WAL lo cubre.
2. **¿Hay un motivo funcional para cambiarlo?** No aparece ninguno. Las
   operaciones que el sistema hace —altas, listados con filtro, agregados para
   el dashboard y la auditoría— son consultas simples sobre tablas pequeñas.
3. **¿Cuánto costaría cambiarlo?** Alto y sin beneficio medido: habría que
   reescribir `database.py`, migrar los datos cifrados y añadir un servicio al
   instalador, que es justo lo que la Fase 7 debe simplificar.

## Qué NO se decide aquí

* **La configuración del asistente no vive en la base.** El proveedor, el
  modelo y el punto de conexión se guardan en `modelos/config.json`, y la clave
  cifrada con la clave local de `modelos/llave.bin` (permisos `0700`/`0600`),
  el mismo patrón que `backend/tokens.py`. Se mantiene así: una credencial no
  es un dato del archivo documental, y mezclarla con la base haría que un
  respaldo de documentos arrastrase una credencial.
* **Los modelos locales (Ollama) siguen aparcados** por decisión de Raven del
  2026-09-30. Esta evaluación no los reintroduce.

## Cuándo habría que revisar esta decisión

Se revisa si aparece alguno de estos hechos, no antes:

* más de un proceso escribiendo en la base a la vez (por ejemplo, si el
  instalador levantara el servicio como *daemon* compartido entre varias
  ventanas o varios usuarios del mismo equipo);
* documentos cifrados en la base que hagan crecer el archivo hasta el punto de
  que las copias de seguridad o el arranque se resientan;
* una necesidad de búsqueda sobre el corpus que SQLite no resuelva —es
  exactamente el terreno de la Fase 5, que evalúa un almacén vectorial **como
  complemento**, no como sustituto—.