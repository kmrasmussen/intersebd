import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App' // We will create this next
import './index.css' // Assuming your global styles are here (Tailwind)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)