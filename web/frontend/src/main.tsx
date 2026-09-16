import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const container = document.getElementById('root')
if (!container) throw new Error('Root element not found')

const root = createRoot(container)

if (import.meta.env.DEV && window.location.pathname === '/preview') {
  import('./preview/PreviewApp.tsx').then(({ default: PreviewApp }) => {
    root.render(
      <StrictMode>
        <PreviewApp />
      </StrictMode>,
    )
  })
} else {
  root.render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}
