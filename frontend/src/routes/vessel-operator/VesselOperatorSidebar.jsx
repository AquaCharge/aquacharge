import { Home, Ship, MapPin, Calendar, FileText, LogOut, User } from "lucide-react"
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
  SidebarTrigger,
} from "@/components/ui/sidebar"

// Vessel Operator menu items
const vesselOperatorItems = [
  {
    title: "Dashboard",
    url: "/",
    icon: Home,
  },
  {
    title: "Find Stations",
    url: "/find-stations",
    icon: MapPin,
  },
  {
    title: "My Bookings",
    url: "/my-bookings",
    icon: Calendar,
  },
  {
    title: "My Vessels",
    url: "/my-vessels",
    icon: Ship,
  },
  {
    title: "My Contracts",
    url: "/my-contracts",
    icon: FileText,
  },
]

export function VesselOperatorSidebar() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const handleLogout = () => {
    logout()
  }

  return (
    <Sidebar collapsible="icon" variant="floating">
      <SidebarHeader className="flex flex-row items-center justify-between gap-2 border-b border-sidebar-border px-3 py-3 group-data-[collapsible=icon]:justify-center">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-cyan-600">
          <svg
            className="h-4 w-4 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
        </div>
        <div className="min-w-0 flex-1 overflow-hidden transition-[opacity,width] duration-200 group-data-[collapsible=icon]:hidden group-data-[collapsible=icon]:flex-none">
          <h2 className="truncate text-base font-semibold text-sidebar-foreground">AquaCharge</h2>
          <p className="truncate text-xs text-sidebar-foreground/70">Vessel Operator</p>
        </div>
        <SidebarTrigger />
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {vesselOperatorItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild tooltip={item.title} isActive={location.pathname === item.url}>
                    <Link to={item.url}>
                      <item.icon className="size-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild tooltip={user?.displayName || "Profile"}>
              <Link to="/profile">
                <User className="size-4" />
                <span>Profile</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={handleLogout} tooltip="Logout">
              <LogOut className="size-4" />
              <span>Logout</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}