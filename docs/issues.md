# improvements

> **Estado: consolidado y corregido (2026-09-30).**
>
> El hallazgo quedó registrado como `SCRUM-89` en `jira.md` y en la Fase 3 de
> `planning.md`. El síntoma («no se puede acceder al dashboard mediante login y
> register») tenía **tres** causas superpuestas:
>
> 1. **El alta de usuario no existía en el frontend.** El backend validaba
>    credenciales y gestionaba el 2FA, pero crear una cuenta seguía siendo
>    exclusivo de `main.py`, así que una instalación nueva no tenía forma de
>    entrar. Se cerró con `SCRUM-57` (`POST /api/registro`,
>    `src/pages/Registro.jsx`).
> 2. **Una base caída se veía como un servicio sano.** `GET /api/salud` no
>    comprobaba la base y el arranque moría con una traza de Python que el
>    lanzador resumía en «servicio no disponible», sin decir por qué. La salud
>    informa ahora del estado real (`SELECT 1`), el arranque anuncia
>    `DATENJAGER_ERROR base de datos: …` y Electron muestra ese mensaje.
> 3. **La causa directa del síntoma: `src/App.jsx` usaba `<Icono>` en la
>    sub-cabecera sin importarlo.** Al montar el shell autenticado saltaba
>    `ReferenceError: Icono is not defined`, React desmontaba el árbol y la
>    ventana quedaba **en blanco justo después de entrar**. Era un defecto
>    previo (ya en `42eeaa8`) e invisible para `vite build`, que compila un
>    identificador sin definir sin quejarse. Corregido con el import.
> 4. **Un puerto 8756 ocupado dejaba la aplicación sin servicio.** Bastaba una
>    instancia anterior que no se cerró bien: el servicio no podía enlazar, la
>    interfaz decía «sin conexión» y el motivo no se pintaba en ninguna pantalla.
>    Ahora se prueban 8756, 8757, 8758, 8759 y, si hace falta, el puerto que elija
>    el sistema; y Bienvenida y Acceso muestran el error real del proceso
>    principal.
> 5. **`npm run dev` no conectaba.** En modo desarrollo el renderer se sirve
>    desde el servidor de Vite, así que su origen deja de ser `file://` y el
>    navegador bloqueaba las llamadas al servicio por CORS
>    (*«has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header»*)
>    pese a que el servicio estaba levantado. Se habilita CORS solo para esos
>    orígenes y solo en desarrollo (`DATENJAGER_CORS_ORIGENES`), nunca en
>    producción.
>
> **Verificación (2026-09-30).** No bastó `vite build`: se condujo la ventana
> real de Electron por CDP, sobre una base temporal, y se completó el recorrido
> entero —bienvenida → registro → alta 2FA con QR → códigos de respaldo →
> dashboard → cerrar sesión → login con 2FA → dashboard—. En la propia SQLite se
> comprobó que el hash es PBKDF2-SHA256 y que el secreto TOTP y los códigos de
> respaldo quedan como `ENCK:` (AES-256-GCM del `EncryptionManager`),
> descifrables con la clave derivada de la contraseña. El modo desarrollo se
> comprobó igual, conduciendo el propio servidor de Vite + Electron con `--dev`.
>
> Suite: `./venv/bin/python -m unittest discover -s tests -t .` → 142 pruebas OK.

conexion a base de datos fallida. origen

conexion electron / web caen


concecuencia.

**no se puede** acceder al dashboard mediante **login** y **register**

consolidar dentro del planning.md | jira.md por si no esta contemplado
