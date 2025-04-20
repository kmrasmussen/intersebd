"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Database, Info, User, LogOut, ChevronLeft, ChevronRight, FileJson, Phone, ListFilter } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function Sidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(true)

  return (
    <div
      className={`h-screen border-r bg-gray-50 flex flex-col relative ${
        collapsed ? "w-16" : "w-64"
      } transition-width duration-300`}
    >
      {/* Header */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Database className="h-6 w-6 shrink-0" />
          <span className={`font-semibold text-lg ${collapsed ? "hidden" : "block"}`}>Annotation Tool</span>
        </div>
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="text-gray-500 hover:text-gray-700 focus:outline-none"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
        </button>
      </div>

      {/* Navigation */}
      <div className="flex-1 overflow-auto">
        <nav className="px-2 py-2">
          <ul className="space-y-1">
            <li>
              <Link
                href="/caller"
                className={`flex items-center gap-3 px-3 py-2 rounded-md hover:bg-gray-200 ${
                  pathname === "/caller" ? "bg-gray-200 font-medium" : ""
                }`}
              >
                <Phone className="h-5 w-5 shrink-0" />
                <span className={collapsed ? "hidden" : "block"}>Caller</span>
              </Link>
            </li>
            <li>
              <Link
                href="/"
                className={`flex items-center gap-3 px-3 py-2 rounded-md hover:bg-gray-200 ${
                  pathname === "/" || pathname === "/requests-v2" ? "bg-gray-200 font-medium" : ""
                }`}
              >
                <ListFilter className="h-5 w-5 shrink-0" />
                <span className={collapsed ? "hidden" : "block"}>Requests Overview</span>
              </Link>
            </li>
            <li>
              <Link
                href="/json-schema"
                className={`flex items-center gap-3 px-3 py-2 rounded-md hover:bg-gray-200 ${
                  pathname === "/json-schema" ? "bg-gray-200 font-medium" : ""
                }`}
              >
                <FileJson className="h-5 w-5 shrink-0" />
                <span className={collapsed ? "hidden" : "block"}>JSON Schema</span>
              </Link>
            </li>
            <li>
              <Link
                href="/generate-dataset"
                className={`flex items-center gap-3 px-3 py-2 rounded-md hover:bg-gray-200 ${
                  pathname === "/generate-dataset" ? "bg-gray-200 font-medium" : ""
                }`}
              >
                <Database className="h-5 w-5 shrink-0" />
                <span className={collapsed ? "hidden" : "block"}>Generate Dataset</span>
              </Link>
            </li>
            <li>
              <Link
                href="/about"
                className={`flex items-center gap-3 px-3 py-2 rounded-md hover:bg-gray-200 ${
                  pathname === "/about" ? "bg-gray-200 font-medium" : ""
                }`}
              >
                <Info className="h-5 w-5 shrink-0" />
                <span className={collapsed ? "hidden" : "block"}>About</span>
              </Link>
            </li>
          </ul>
        </nav>
      </div>

      {/* Footer with user profile */}
      <div className="p-2 border-t mt-auto">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 w-full p-2 hover:bg-gray-200 rounded-md">
              <Avatar className="h-8 w-8 shrink-0">
                <AvatarImage src="/placeholder.svg" alt="User" />
                <AvatarFallback>U</AvatarFallback>
              </Avatar>
              <div className={`flex-1 text-left ${collapsed ? "hidden" : "block"}`}>
                <p className="text-sm font-medium">User Name</p>
                <p className="text-xs text-gray-500">admin@example.com</p>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
