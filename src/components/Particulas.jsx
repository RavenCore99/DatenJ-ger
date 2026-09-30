import { useEffect, useRef } from 'react'

import { useApp } from '../estado/ProveedorApp.jsx'

/**
 * Sistema de partículas (SCRUM-71).
 *
 * Portado del complemento `assets/assets/dynamic_t_particle system`, pero con
 * la estética del proyecto: sin el arcoíris ni el degradado del original —usa
 * el azul primario y el acento del sistema—, densidad contenida y sin
 * interacción de clic. Es un fondo decorativo para las pantallas de entrada.
 *
 * La paleta se relee cuando cambia el tema, porque el lienzo no entiende las
 * variables CSS y hay que resolver los valores a RGB.
 *
 * Con el movimiento desactivado pinta un campo estático y no entra en bucle.
 */
export default function Particulas({ className = '', densidad = 1 }) {
  const { animaciones } = useApp()
  const lienzo = useRef(null)

  useEffect(() => {
    const canvas = lienzo.current
    if (!canvas) return undefined

    const ctx = canvas.getContext('2d')
    let ancho = 0
    let alto = 0
    let puntos = []
    let cuadro = null
    let paleta = { primario: '29,78,216', acento: '0,99,152' }
    const raton = { x: null, y: null }

    const leerPaleta = () => {
      const est = globalThis.getComputedStyle(document.documentElement)
      const a = (est.getPropertyValue('--dj-primario').trim() || '29 78 216').split(/\s+/).join(',')
      const b = (est.getPropertyValue('--dj-acento').trim() || '0 99 152').split(/\s+/).join(',')
      paleta = { primario: a, acento: b }
    }

    const ajustar = () => {
      const rect = canvas.getBoundingClientRect()
      ancho = canvas.width = Math.max(1, Math.floor(rect.width))
      alto = canvas.height = Math.max(1, Math.floor(rect.height))

      const cantidad = Math.round(Math.min(70, Math.max(16, (ancho * alto) / 26000)) * densidad)
      puntos = Array.from({ length: cantidad }, () => ({
        x: Math.random() * ancho,
        y: Math.random() * alto,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        r: Math.random() * 1.6 + 0.6,
      }))
    }

    const pintar = () => {
      ctx.clearRect(0, 0, ancho, alto)

      for (const punto of puntos) {
        if (animaciones) {
          punto.x += punto.vx
          punto.y += punto.vy
        }
        if (punto.x <= 0 || punto.x >= ancho) punto.vx *= -1
        if (punto.y <= 0 || punto.y >= alto) punto.vy *= -1

        // El ratón aparta suavemente las partículas cercanas.
        if (raton.x !== null) {
          const dx = punto.x - raton.x
          const dy = punto.y - raton.y
          const dist2 = dx * dx + dy * dy
          if (dist2 < 12000 && dist2 > 0.01) {
            const fuerza = (12000 - dist2) / 12000
            const dist = Math.sqrt(dist2)
            punto.x += (dx / dist) * fuerza * 1.4
            punto.y += (dy / dist) * fuerza * 1.4
          }
        }
      }

      // Enlaces entre partículas próximas.
      ctx.lineWidth = 1
      for (let i = 0; i < puntos.length; i++) {
        for (let j = i + 1; j < puntos.length; j++) {
          const dx = puntos[i].x - puntos[j].x
          const dy = puntos[i].y - puntos[j].y
          const dist2 = dx * dx + dy * dy
          if (dist2 < 12000) {
            const alfa = (1 - Math.sqrt(dist2) / 110) * 0.2
            ctx.strokeStyle = `rgba(${paleta.primario}, ${alfa})`
            ctx.beginPath()
            ctx.moveTo(puntos[i].x, puntos[i].y)
            ctx.lineTo(puntos[j].x, puntos[j].y)
            ctx.stroke()
          }
        }
      }

      for (const punto of puntos) {
        ctx.fillStyle = `rgba(${paleta.primario}, 0.55)`
        ctx.beginPath()
        ctx.arc(punto.x, punto.y, punto.r, 0, Math.PI * 2)
        ctx.fill()
      }

      if (animaciones) cuadro = requestAnimationFrame(pintar)
    }

    const alMover = (evento) => {
      const rect = canvas.getBoundingClientRect()
      raton.x = evento.clientX - rect.left
      raton.y = evento.clientY - rect.top
    }

    const alSalir = () => {
      raton.x = null
      raton.y = null
    }

    leerPaleta()
    ajustar()
    pintar()

    const observador = new MutationObserver(() => {
      leerPaleta()
      if (!animaciones) pintar()
    })
    observador.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })

    globalThis.addEventListener('resize', ajustar)
    canvas.addEventListener('mousemove', alMover)
    canvas.addEventListener('mouseleave', alSalir)

    return () => {
      if (cuadro) cancelAnimationFrame(cuadro)
      observador.disconnect()
      globalThis.removeEventListener('resize', ajustar)
      canvas.removeEventListener('mousemove', alMover)
      canvas.removeEventListener('mouseleave', alSalir)
    }
  }, [animaciones, densidad])

  return <canvas ref={lienzo} aria-hidden="true" className={className} />
}