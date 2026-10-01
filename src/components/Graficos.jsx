/**
 * Gráficos del dashboard (SCRUM-82).
 *
 * La **lógica** de los datos vive en Python (`backend/services/reportes.py`):
 * métricas, distribución, serie temporal y la regresión con predicción y R².
 * Aquí solo se dibuja, con la paleta del sistema, y sin traer una librería de
 * charts: son formas SVG y utilidades de Tailwind, así que no hay dependencias
 * nuevas.
 *
 * Los roles de color los decide el backend (`PALETA_GRAFICOS` viaja como rol
 * semántico: `primario`, `acento`, `exito`, `alerta`, `peligro`) y este módulo
 * los resuelve contra los tokens `--dj-*`. Las clases se escriben literales
 * —Tailwind no ve las que se construyen con plantillas—, por eso hay mapas.
 */

/** Orden de los roles de serie, el mismo que declara el backend. */
export const ROLES_SERIE = ['primario', 'acento', 'exito', 'alerta', 'peligro']

const CLASE_TRAZO = {
  primario: 'stroke-primario',
  acento: 'stroke-acento',
  exito: 'stroke-exito',
  alerta: 'stroke-alerta',
  peligro: 'stroke-peligro',
}

const CLASE_RELLENO = {
  primario: 'fill-primario',
  acento: 'fill-acento',
  exito: 'fill-exito',
  alerta: 'fill-alerta',
  peligro: 'fill-peligro',
}

const CLASE_FONDO = {
  primario: 'bg-primario',
  acento: 'bg-acento',
  exito: 'bg-exito',
  alerta: 'bg-alerta',
  peligro: 'bg-peligro',
}

/** Rol de la serie en la posición `indice`, con vuelta al principio. */
export function rolDeSerie(indice) {
  return ROLES_SERIE[indice % ROLES_SERIE.length]
}

/* ------------------------------------------------------------------ */

/**
 * Medidor semicircular. El arco se llena en proporción al máximo del conjunto;
 * el valor va en monoespaciada dentro del arco.
 */
export function Medidor({ etiqueta, valor, maximo, rol = 'primario', texto }) {
  const proporcion = maximo > 0 ? Math.min(valor / maximo, 1) : 0
  const arco = 'M 10 50 A 40 40 0 0 1 90 50'

  return (
    <div className="flex flex-col items-center gap-1.5">
      <svg
        viewBox="0 0 100 56"
        className="h-14 w-full max-w-[7.5rem]"
        role="img"
        aria-label={`${etiqueta}: ${texto ?? valor}`}
      >
        <path
          d={arco}
          pathLength="100"
          fill="none"
          strokeWidth="9"
          strokeLinecap="round"
          className="stroke-fondo-2"
        />
        <path
          d={arco}
          pathLength="100"
          fill="none"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray="100"
          strokeDashoffset={100 * (1 - proporcion)}
          className={`${CLASE_TRAZO[rol] ?? CLASE_TRAZO.primario} transition-all duration-500`}
        />
        <text
          x="50"
          y="46"
          textAnchor="middle"
          className="fill-texto font-mono"
          fontSize="15"
        >
          {texto ?? valor}
        </text>
      </svg>
      <p className="text-center text-etiqueta-sm uppercase tracking-wider text-tenue">
        {etiqueta}
      </p>
    </div>
  )
}

/* ------------------------------------------------------------------ */

/**
 * Anillo de distribución. Cada porción es un tramo del mismo círculo,
 * separado por su `stroke-dasharray`.
 */
export function Donut({ elementos, vacio = 'Sin datos todavía' }) {
  const total = elementos.reduce((suma, { valor }) => suma + valor, 0)

  if (!total) {
    return <p className="py-8 text-center text-cuerpo-sm text-tenue">{vacio}</p>
  }

  const radio = 38
  const circunferencia = 2 * Math.PI * radio
  let acumulado = 0

  const porciones = elementos.map((elemento, indice) => {
    const largo = (elemento.valor / total) * circunferencia
    const porcion = {
      ...elemento,
      rol: rolDeSerie(indice),
      largo,
      desplazamiento: -acumulado,
      porcentaje: Math.round((elemento.valor / total) * 100),
    }
    acumulado += largo
    return porcion
  })

  return (
    <div className="flex flex-wrap items-center gap-6">
      <svg viewBox="0 0 100 100" className="h-40 w-40 shrink-0" role="img" aria-label="Distribución">
        <g transform="rotate(-90 50 50)">
          {porciones.map((porcion) => (
            <circle
              key={porcion.etiqueta}
              cx="50"
              cy="50"
              r={radio}
              fill="none"
              strokeWidth="14"
              strokeDasharray={`${porcion.largo} ${circunferencia - porcion.largo}`}
              strokeDashoffset={porcion.desplazamiento}
              className={`${CLASE_TRAZO[porcion.rol]} transition-all duration-500`}
            />
          ))}
        </g>
        <text
          x="50"
          y="48"
          textAnchor="middle"
          className="fill-texto font-mono"
          fontSize="18"
        >
          {total}
        </text>
        <text
          x="50"
          y="62"
          textAnchor="middle"
          className="fill-tenue"
          fontSize="8"
        >
          documentos
        </text>
      </svg>

      <ul className="flex min-w-[10rem] flex-1 flex-col gap-1.5">
        {porciones.map((porcion) => (
          <li key={porcion.etiqueta} className="flex items-center gap-2 text-cuerpo-sm">
            <span
              aria-hidden="true"
              className={`h-2.5 w-2.5 shrink-0 rounded-full ${
                CLASE_FONDO[porcion.rol] ?? CLASE_FONDO.primario
              }`}
            />
            <span className="min-w-0 flex-1 truncate text-texto-2" title={porcion.etiqueta}>
              {porcion.etiqueta}
            </span>
            <span className="shrink-0 font-mono text-tenue">{porcion.porcentaje}%</span>
            <span className="w-8 shrink-0 text-right font-mono">{porcion.valor}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}

/* ------------------------------------------------------------------ */

/**
 * Serie temporal con barras, la recta de regresión, el punto de predicción y
 * el coeficiente R². Todo llega calculado desde el backend (SCRUM-81).
 */
export function LineaTendencia({ tendencia }) {
  const {
    dias = [],
    valores = [],
    linea = [],
    prediccion = null,
    r2 = null,
    paleta = {},
  } = tendencia ?? {}

  if (!dias.length) {
    return (
      <p className="py-8 text-center text-cuerpo-sm text-tenue">
        Sin datos temporales. Sube documentos para ver la tendencia.
      </p>
    )
  }

  const ANCHO = 100
  const ALTO = 64
  const ranuras = dias.length + (prediccion !== null ? 1 : 0)
  const paso = ANCHO / ranuras
  const centro = (indice) => paso * indice + paso / 2

  const maximo = Math.max(...valores, prediccion ?? 0, 1)
  const y = (valor) => ALTO - 6 - (Math.max(valor, 0) / maximo) * (ALTO - 14)

  const anchoBarra = Math.max(Math.min(paso * 0.55, 6), 1)
  const rolBarras = paleta.barras_temporales ?? 'primario'
  const rolTendencia = paleta.tendencia ?? 'alerta'
  const rolPrediccion = paleta.prediccion ?? 'peligro'

  const puntosRecta = linea
    .map((valor, indice) => `${centro(indice).toFixed(2)},${y(valor).toFixed(2)}`)
    .join(' ')

  return (
    <div className="flex flex-col gap-3">
      <svg
        viewBox={`0 0 ${ANCHO} ${ALTO}`}
        preserveAspectRatio="none"
        className="h-44 w-full"
        role="img"
        aria-label="Actividad temporal con regresión lineal"
      >
        {valores.map((valor, indice) => (
          <rect
            key={dias[indice]}
            x={centro(indice) - anchoBarra / 2}
            y={y(valor)}
            width={anchoBarra}
            height={ALTO - y(valor)}
            rx="0.6"
            className={`${CLASE_RELLENO[rolBarras] ?? CLASE_RELLENO.primario} opacity-70`}
          />
        ))}

        <line
          x1="0"
          y1={ALTO - 5}
          x2={ANCHO}
          y2={ALTO - 5}
          strokeWidth="0.4"
          className="stroke-borde"
        />

        {linea.length >= 2 && (
          <polyline
            points={puntosRecta}
            fill="none"
            strokeWidth="1.2"
            strokeDasharray="3 2"
            strokeLinecap="round"
            vectorEffect="non-scaling-stroke"
            className={CLASE_TRAZO[rolTendencia] ?? CLASE_TRAZO.alerta}
          />
        )}

        {prediccion !== null && (
          <rect
            x={centro(dias.length) - 1.4}
            y={y(prediccion) - 1.4}
            width="2.8"
            height="2.8"
            transform={`rotate(45 ${centro(dias.length)} ${y(prediccion)})`}
            className={CLASE_RELLENO[rolPrediccion] ?? CLASE_RELLENO.peligro}
          />
        )}
      </svg>

      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-cuerpo-sm">
        <span className="flex flex-wrap items-center gap-3 text-tenue">
          <Leyenda rol={rolBarras} texto="Subidas por día" />
          {linea.length >= 2 && <Leyenda rol={rolTendencia} texto="Tendencia" linea />}
          {prediccion !== null && <Leyenda rol={rolPrediccion} texto="Predicción" />}
        </span>
        <span className="flex items-center gap-3 font-mono text-tenue">
          {tendencia?.pendiente != null && (
            <span title="Pendiente de la recta por mínimos cuadrados">
              m={tendencia.pendiente >= 0 ? '+' : ''}
              {tendencia.pendiente.toFixed(2)}
            </span>
          )}
          {r2 !== null && <span title="Coeficiente de determinación">R²={r2.toFixed(3)}</span>}
          {prediccion !== null && (
            <span className="text-texto-2" title="Documentos previstos para el día siguiente">
              previsión {Math.round(prediccion)}
            </span>
          )}
        </span>
      </div>

      <p className="text-cuerpo-sm text-tenue">
        {linea.length >= 2
          ? `Ajuste lineal sobre ${dias.length} día(s) con altas registradas.`
          : 'Hacen falta al menos dos días con altas para ajustar la recta.'}
      </p>
    </div>
  )
}

/** Muestra de color con su etiqueta, para la leyenda del gráfico. */
function Leyenda({ rol, texto, linea = false }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        aria-hidden="true"
        className={
          linea
            ? `h-0 w-4 border-t-2 border-dashed ${
                { primario: 'border-primario', acento: 'border-acento', exito: 'border-exito', alerta: 'border-alerta', peligro: 'border-peligro' }[rol] ??
                'border-alerta'
              }`
            : `h-2.5 w-2.5 rounded-sm ${CLASE_FONDO[rol] ?? CLASE_FONDO.primario}`
        }
      />
      {texto}
    </span>
  )
}