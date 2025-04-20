import "@/styles/globals.css"
import { Sidebar } from "@/components/sidebar"
import { ThemeProvider } from "@/components/theme-provider"
import { Outlet } from "react-router-dom";
// *** IMPORT SHARED TYPES ***
import { LoginStatusResponse } from "../types"; // Adjust path if needed

interface LayoutProps {
  userStatus: LoginStatusResponse | null; // Use imported type
}

export default function Layout({ userStatus }: LayoutProps) {
  const defaultStatus: LoginStatusResponse = { is_logged_in: false, is_guest: false, user_info: null }; // Use imported type

  return (
    <ThemeProvider attribute="class" defaultTheme="light" enableSystem={false} forcedTheme="light">
      <div className="flex h-screen bg-gray-100 font-sans">
        <Sidebar userStatus={userStatus || defaultStatus} />
        <main className="flex-1 overflow-auto p-4 md:p-6 bg-white">
          <Outlet />
        </main>
      </div>
    </ThemeProvider>
  );
}
