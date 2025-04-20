import "@/styles/globals.css"
import { Sidebar } from "@/components/sidebar"
import { ThemeProvider } from "@/components/theme-provider"
import { Outlet } from "react-router-dom";

export default function Layout() {
  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} forcedTheme="light">
      <div className="flex h-screen bg-gray-100 font-sans">
        <Sidebar />
        <main className="flex-1 overflow-auto bg-white">
          <Outlet />
        </main>
      </div>
    </ThemeProvider>
  )
}
