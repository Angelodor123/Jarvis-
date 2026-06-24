import React from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'

// StrictMode intentionally omitted — double-render invocations caused the
// storage write bug described in spec §13. Storage writes now live outside
// setState callbacks so this is safe to add back later if desired.
createRoot(document.getElementById('root')).render(<App />)
