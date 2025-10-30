import { Home, Ship, MapPin, Calendar, Search, LogOut, User } from "lucide-react"
import { Link } from 'react-router-dom'
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
]

export function VesselOperatorSidebar() {
  const { user, logout } = useAuth()

  const handleLogout = () => {
    logout()
  }

  return (
    <Sidebar>
      <SidebarHeader>
        <div className="flex items-center space-x-2 px-4 py-2">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-lg flex items-center justify-center">
            <svg
              className="w-4 h-4 text-white"
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
          <div>
            <h2 className="text-lg font-bold text-gray-900">AquaCharge</h2>
            <p className="text-xs text-gray-500">Vessel Operator</p>
          </div>
        </div>
      </SidebarHeader>
      
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {vesselOperatorItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild>
                    <Link to={item.url} className="flex items-center space-x-2">
                      <item.icon className="w-4 h-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <div className="px-4 py-2 border-t">
              <Link 
                to="/profile" 
                className="flex items-center space-x-2 mb-2 p-2 hover:bg-gray-100 rounded-md transition-colors cursor-pointer"
              >
                <User className="w-4 h-4 text-gray-600" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {user?.displayName || 'User'}
                  </p>
                  <p className="text-xs text-gray-500 truncate">
                    {user?.email || ''}
                  </p>
                </div>
              </Link>
              <button
                onClick={handleLogout}
                className="flex items-center space-x-2 w-full px-2 py-1 text-sm text-red-600 hover:bg-red-50 rounded-md transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span>Logout</span>
              </button>
            </div>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}