import { useState } from 'react'

import { useApp } from '../estado/ProveedorApp.jsx'
import { backend } from '../lib/api.js'
import MarcoAcceso from '../components/MarcoAcceso.jsx'
import AltaSegundoFactor from '../components/AltaSegundoFactor.jsx'
import Icono from '../components/Icono.jsx'
import logo from '../../assets/logo/logo.png'

/**
 * Registro de operadores (SCRUM-57) con el alta del segundo factor (SCRUM-58).
 *
 * Era la última pantalla que faltaba para poder usar el sistema desde cero: el
 * backend ya validaba credenciales y gestionaba el 2FA, pero dar de alta una
 * cuenta seguía siendo exclusivo de `main.py`, así que una instalación nueva no
 * tenía forma de entrar. Con esto, el recorrido completo —registro → segundo
 * factor → códigos de respaldo → sistema— se hace dentro del frontend.
 *
 * El alta la ejecuta el backend (`POST /api/registro`): valida las reglas,
 * guarda el hash PBKDF2 y abre la sesión del usuario nuevo. Esta pantalla solo
 * recoge los datos y encadena el paso siguiente; nunca maneja claves.
 *
 * Mientras la sesión del alta está abierta, el portal sigue mostrándose: el
 * segundo factor se configura antes de entrar al sistema, no después.
 */
export default function Registro({ onVolver, onTerminar }) {
  const { conectado } = useApp()

  const [paso, setPaso] = useState('datos')
  const [nombre, setNombre] = useState('')
  const [contrasena, setContrasena] = useState('')
  const [repetida, setRepetida] = useState('')
  const [mostrar, setMostrar] = useState(false)
  const [error, setError] = useState(null)
  const [ocupado, setOcupado] = useState(false)

  const fuerza = fortaleza(contrasena)
  const corta = contrasena.length > 0 && contrasena.length < 8
  const distinta = repetida.length > 0 && contrasena !== repetida
  const nombreCorto = nombre.length > 0 && nombre.trim().length < 3

  const registrar = async (evento) => {
    evento.preventDefault()
    setOcupado(true)
    setError(null)

    try {
      await backend.sesion.registrar(nombre.trim(), contrasena)
      setContrasena('')
      setRepetida('')
      setPaso('segundo_factor')
    } catch (fallo) {
      setError(fallo.message)
    } finally {
      setOcupado(false)
    }
  }

  return (
    <MarcoAcceso
      titulo="Alta de operador"
      subtitulo="Volver a la bienvenida"
      onVolver={onVolver}
    >
      <main className="aparecer flex min-h-0 flex-1 items-center justify-center overflow-y-auto p-8">
        <div className="w-full max-w-[32rem] overflow-hidden rounded-panel border border-borde bg-superficie shadow-flotante">
          <div
            aria-hidden="true"
            className="h-1 bg-gradient-to-r from-primario-enfasis via-primario to-acento"
          />

          <div className="flex flex-col gap-5 p-7">
            <header className="flex flex-col items-center gap-3 text-center">
              <img
                src={logo}
                alt="DatenJäger"
                className="h-16 w-16 rounded-full object-contain ring-2 ring-primario/40"
              />
              <div>
                <h1 className="font-marca text-titulo-md tracking-tight text-primario">
                  {paso === 'datos' ? 'Registro de operador' : 'Configuración del doble factor'}
                </h1>
                <p className="text-cuerpo-sm text-tenue">
                  {paso === 'datos'
                    ? 'Crea la cuenta con la que entrarás a la bóveda'
                    : `Cuenta «${nombre.trim()}» creada · falta el segundo paso`}
                </p>
              </div>
            </header>

            {!conectado && (
              <Aviso tipo="peligro">
                Sin conexión con el servicio local: no es posible registrar la cuenta.
              </Aviso>
            )}

            {error && <Aviso tipo="peligro">{error}</Aviso>}

            {paso === 'datos' && (
              <form className="flex flex-col gap-4" onSubmit={registrar}>
                <Campo
                  etiqueta="Usuario"
                  valor={nombre}
                  autoComplete="username"
                  autoFocus
                  ayuda="Al menos 3 caracteres. Es el nombre con el que te identificarás."
                  onCambio={setNombre}
                />

                <Campo
                  etiqueta="Contraseña"
                  tipo={mostrar ? 'text' : 'password'}
                  valor={contrasena}
                  autoComplete="new-password"
                  mono
                  accion={
                    <button
                      type="button"
                      onClick={() => setMostrar((valor) => !valor)}
                      className="text-etiqueta-sm text-tenue transition-colors hover:text-primario"
                    >
                      {mostrar ? 'Ocultar' : 'Mostrar'}
                    </button>
                  }
                  onCambio={setContrasena}
                />

                {contrasena.length > 0 && <MedidorFuerza fuerza={fuerza} />}

                <Campo
                  etiqueta="Repite la contraseña"
                  tipo={mostrar ? 'text' : 'password'}
                  valor={repetida}
                  autoComplete="new-password"
                  onCambio={setRepetida}
                />

                {nombreCorto && <Aviso tipo="alerta">El usuario necesita 3 caracteres como mínimo.</Aviso>}
                {corta && <Aviso tipo="alerta">La contraseña debe tener al menos 8 caracteres.</Aviso>}
                {distinta && <Aviso tipo="alerta">Las contraseñas no coinciden.</Aviso>}
                {!corta && contrasena.length > 0 && fuerza.puntaje < 2 && (
                  <Aviso tipo="alerta">
                    Contraseña {fuerza.etiqueta.toLowerCase()}: añade mayúsculas, números o símbolos.
                  </Aviso>
                )}

                <button
                  type="submit"
                  disabled={ocupado || !conectado || !nombre || !contrasena || corta || distinta || fuerza.puntaje < 2}
                  className="flex items-center justify-center gap-2 rounded-lg bg-primario px-4 py-2.5 text-etiqueta-md font-medium text-sobre-primario transition-colors hover:bg-primario-enfasis disabled:opacity-50"
                >
                  {ocupado ? 'Creando la cuenta…' : 'Crear la cuenta'}
                  {!ocupado && <Icono nombre="flecha-derecha" tamano={15} />}
                </button>

                <p className="border-t border-borde pt-3 text-cuerpo-sm text-tenue">
                  La contraseña se convierte en un hash PBKDF2-SHA256 (260 000 rondas) antes de
                  guardarse. El texto original no se conserva en ningún sitio.
                </p>
              </form>
            )}

            {paso === 'segundo_factor' && (
              <AltaSegundoFactor onTerminar={onTerminar} textoTerminar="Entrar al sistema" />
            )}
          </div>
        </div>
      </main>
    </MarcoAcceso>
  )
}

/* ------------------------------------------------------------------ */

/**
 * Fortaleza de la contraseña, con la misma regla que `password_strength` de
 * `database.py`: longitud, mayúsculas, dígitos y símbolos. Es solo el aviso
 * inmediato; la validación que decide es la del backend.
 */
function fortaleza(valor) {
  let puntaje = 0
  if (valor.length >= 8) puntaje += 1
  if (/[A-Z]/.test(valor)) puntaje += 1
  if (/[0-9]/.test(valor)) puntaje += 1
  if (/[^A-Za-z0-9]/.test(valor)) puntaje += 1

  const etiquetas = ['Muy débil', 'Débil', 'Regular', 'Fuerte', 'Muy fuerte']
  return { puntaje, etiqueta: etiquetas[puntaje] }
}

function MedidorFuerza({ fuerza }) {
  const colores = ['bg-peligro', 'bg-peligro', 'bg-alerta', 'bg-exito', 'bg-exito']

  return (
    <div className="flex flex-col gap-1.5" aria-live="polite">
      <div className="flex gap-1">
        {[0, 1, 2, 3].map((indice) => (
          <span
            key={indice}
            className={`h-1 flex-1 rounded-full ${
              indice < fuerza.puntaje ? colores[fuerza.puntaje] : 'bg-fondo-2'
            }`}
          />
        ))}
      </div>
      <span className="text-etiqueta-sm text-tenue">Fortaleza: {fuerza.etiqueta}</span>
    </div>
  )
}

function Aviso({ tipo, children }) {
  const clases = {
    peligro: 'border-peligro/40 bg-peligro/5 text-peligro',
    alerta: 'border-alerta/40 bg-alerta/5 text-alerta',
  }[tipo]

  return (
    <p role="alert" className={`rounded-lg border px-3 py-2 text-cuerpo-sm ${clases}`}>
      {children}
    </p>
  )
}

function Campo({ etiqueta, valor, onCambio, tipo = 'text', ayuda, accion, mono, ...resto }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="flex items-center justify-between gap-2">
        <span className="text-etiqueta-sm text-texto">{etiqueta}</span>
        {accion}
      </span>

      <input
        type={tipo}
        value={valor}
        required
        onChange={(evento) => onCambio(evento.target.value)}
        className={[
          'rounded-lg border border-borde bg-fondo px-3 py-2 text-cuerpo-md outline-none',
          'transition-colors focus:border-primario focus:ring-1 focus:ring-primario',
          mono ? 'font-mono tracking-widest' : '',
        ].join(' ')}
        {...resto}
      />

      {ayuda && <span className="text-cuerpo-sm text-tenue">{ayuda}</span>}
    </label>
  )
}