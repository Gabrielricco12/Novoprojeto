import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
// A extensão do arquivo foi corrigida de .tsx para .jsx
import App from './App.jsx' 

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
