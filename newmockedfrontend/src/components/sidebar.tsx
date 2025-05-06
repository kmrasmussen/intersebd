"use client"

import { useState } from "react"
import { Link, useLocation, useParams } from "react-router-dom";
import { Database, LogOut, ChevronLeft, ChevronRight, FileJson, Phone, ListFilter, LogIn } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
// *** IMPORT SHARED TYPES ***
import { LoginStatusResponse } from "../types"; // Adjust path if needed

// Define the props type using imported type
interface SidebarProps {
  userStatus: LoginStatusResponse; // Use imported type (Layout ensures it's not null here)
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export function Sidebar({ userStatus }: SidebarProps) {
  const location = useLocation();
  const pathname = location.pathname;
  const { projectId } = useParams<{ projectId: string }>();
  const [collapsed, setCollapsed] = useState(true)

  const getProjectPath = (path: string) => {
    if (!projectId) return path
    const cleanPath = path.startsWith("/") ? path : `/${path}`
    return `/${projectId}${cleanPath === "/" ? "" : cleanPath}`
  }

  const isActive = (path: string) => {
    const fullPath = getProjectPath(path);
    if (path === "/") {
      return pathname === fullPath;
    }
    return pathname.startsWith(fullPath);
  }

  const handleGoogleLogin = () => {
    window.location.href = `${API_BASE_URL}/auth/login/google`;
  };

  const handleLogout = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'GET',
            credentials: 'include',
        });
        if (response.ok) {
            localStorage.removeItem('guestUserId');
            window.location.href = '/';
        } else {
            console.error("Logout failed:", response.statusText);
        }
    } catch (error) {
        console.error("Error during logout:", error);
    }
  };

  const displayName = userStatus.user_info?.name || (userStatus.is_guest ? "Guest User" : "Unknown");
  const displayDetail = userStatus.user_info?.email || (userStatus.is_guest ? `ID: ${userStatus.user_info?.id.substring(0, 8)}...` : "");
  const avatarFallback = displayName.charAt(0).toUpperCase();

  return (
    <div
      className={`h-screen border-r bg-gray-50 flex flex-col relative ${
        collapsed ? "w-16" : "w-64"
      } transition-width duration-300`}
    >
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="h-6 w-6 shrink-0" />
          <span className={`font-semibold text-lg ${collapsed ? "hidden" : "block"}`}>intercebd</span>
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-gray-500 hover:text-gray-700 focus:outline-none"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      <div className="flex-1 overflow-auto">
        <nav className="px-2 py-2">
          <ul className="space-y-1">
            <li>
              <Link
                to={getProjectPath("/")}
                className={`flex items-center gap-3 px-3 py-2 rounded-md hover:bg-gray-200 ${
                  pathname === getProjectPath("/") ? "bg-gray-200 font-medium" : ""
                }`}
              >
                <ListFilter className="h-5 w-5 shrink-0" />
                <span className={collapsed ? "hidden" : "block"}>Requests Overview</span>
              </Link>
            </li>
          </ul>
        </nav>
      </div>

      <div className="p-2 border-t mt-auto">
        {userStatus.is_logged_in ? (
          // --- User is Logged In (e.g., Google): Show Info + Logout Button ---
          <div className="space-y-2">
            {/* User Info Display */}
            <div className="flex items-center gap-2 w-full p-2 rounded-md text-left">
              <Avatar className="h-8 w-8 shrink-0 border">
                <AvatarImage src={"/placeholder.svg"} alt={displayName} />
                <AvatarFallback>{avatarFallback}</AvatarFallback>
              </Avatar>
              <div className={`flex-1 overflow-hidden ${collapsed ? "hidden" : "block"}`}>
                <p className="text-sm font-medium truncate">{displayName}</p>
                <p className="text-xs text-gray-500 truncate">{displayDetail}</p>
              </div>
            </div>

            {/* Logout Button */}
            <button
              onClick={handleLogout}
              className={`flex items-center gap-3 w-full p-2 rounded-md text-red-600 hover:bg-red-100 hover:text-red-700 ${collapsed ? "justify-center" : ""}`}
            >
              <LogOut size={18} className="shrink-0" />
              <span className={`text-sm font-medium ${collapsed ? "hidden" : "block"}`}>Log out</span>
            </button>
          </div>
        ) : userStatus.is_guest ? (
          // --- User is Guest: Show Guest Info + Login with Google Button ---
          <div className="space-y-2">
            {/* User Info Display (Guest) */}
            <div className="flex items-center gap-2 w-full p-2 rounded-md text-left">
              <Avatar className="h-8 w-8 shrink-0 border">
                <AvatarImage src={"/guest-avatar.svg"} alt={displayName} />
                <AvatarFallback>{avatarFallback}</AvatarFallback>
              </Avatar>
              <div className={`flex-1 overflow-hidden ${collapsed ? "hidden" : "block"}`}>
                <p className="text-sm font-medium truncate">{displayName}</p>
                <p className="text-xs text-gray-500 truncate">{displayDetail}</p>
              </div>
            </div>

            {/* Login with Google Button */}
            <button
              onClick={handleGoogleLogin}
              className={`flex items-center gap-3 w-full p-2 rounded-md text-gray-700 hover:bg-blue-100 hover:text-blue-700 ${collapsed ? "justify-center" : ""}`}
            >
              <LogIn size={18} className="shrink-0 text-blue-600" />
              <span className={`text-sm font-medium ${collapsed ? "hidden" : "block"}`}>Login with Google</span>
            </button>
          </div>
        ) : (
          // --- User is Not Identified: Show Login Button ---
          <button
            onClick={handleGoogleLogin}
            className={`flex items-center gap-3 w-full p-2 rounded-md text-gray-700 hover:bg-blue-100 hover:text-blue-700 ${collapsed ? "justify-center" : ""}`}
          >
            <LogIn size={18} className="shrink-0 text-blue-600" />
            <span className={`text-sm font-medium ${collapsed ? "hidden" : "block"}`}>Login with Google</span>
          </button>
        )}
      </div>
    </div>
  )
}
