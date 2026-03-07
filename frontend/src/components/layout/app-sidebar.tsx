import { Home, Ship, MapPin, LogOut, User } from "lucide-react"
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

// Menu items.
const items = [
  {
    title: "Home",
    url: "/",
    icon: Home,
  },
  {
    title: "Stations",
    url: "/stations",
    icon: MapPin,
  },
  {
    title: "Vessels",
    url: "/vessels",
    icon: Ship,
  },
]

export function AppSidebar() {
  const { user, logout } = useAuth()
  const location = useLocation()

  const handleLogout = () => {
    logout()
  }

  return (
    <Sidebar collapsible="icon" variant="floating">
      <SidebarHeader className="flex flex-row items-center justify-between gap-2 border-b border-sidebar-border px-3 py-3 group-data-[collapsible=icon]:justify-center">
        <div className="flex h-9 shrink-0 items-center justify-center overflow-hidden group-data-[collapsible=icon]:w-9 group-data-[collapsible=icon]:flex-none">
          <img
            src="/aquacharge-logo.png"
            alt="AquaCharge"
            className="h-8 w-auto max-w-[10rem] object-contain object-left group-data-[collapsible=icon]:max-w-none group-data-[collapsible=icon]:w-8"
          />
        </div>
        <div className="min-w-0 flex-1 overflow-hidden transition-[opacity,width] duration-200 group-data-[collapsible=icon]:hidden group-data-[collapsible=icon]:flex-none">
          <span className="truncate text-base font-semibold text-sidebar-foreground">AquaCharge</span>
        </div>
        <SidebarTrigger />
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => (
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
        <SidebarGroup>
          <SidebarGroupContent>
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
                <SidebarMenuButton onClick={handleLogout} tooltip="Sign Out">
                  <LogOut className="size-4" />
                  <span>Sign Out</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarFooter>
    </Sidebar>
  )
}