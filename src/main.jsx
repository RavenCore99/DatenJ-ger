import React from 'react'
import { createRoot } from 'react-dom/client'

import App from './App.jsx'
import './index.css'

const contenedor = document.getElementById('root')

if (!contenedor) {
  throw new Error('No se encontró el contenedor #root en index.html')
}

createRoot(contenedor).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)