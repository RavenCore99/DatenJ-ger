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
>
> **Verificación (2026-09-30).** No bastó `vite build`: se condujo la ventana
> real de Electron por CDP, sobre una base temporal, y se completó el recorrido
> entero —bienvenida → registro → alta 2FA con QR → códigos de respaldo →
> dashboard → cerrar sesión → login con 2FA → dashboard—. En la propia SQLite se
> comprobó que el hash es PBKDF2-SHA256 y que el secreto TOTP y los códigos de
> respaldo quedan como `ENCK:` (AES-256-GCM del `EncryptionManager`),
> descifrables con la clave derivada de la contraseña.
>
> Suite: `./venv/bin/python -m unittest discover -s tests -t .` → 142 pruebas OK.

conexion a base de datos fallida. origen

conexion electron / web caen


concecuencia.

**no se puede** acceder al dashboard mediante **login** y **register**

consolidar dentro del planning.md | jira.md por si no esta contemplado
