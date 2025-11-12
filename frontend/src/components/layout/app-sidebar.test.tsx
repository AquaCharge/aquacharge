import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AppSidebar } from './app-sidebar'
import { test, expect, vi } from 'vitest'

// Mock useAuth
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: null,
    logout: vi.fn(),
  }),
}))

// Mock the sidebar components to avoid the provider issue
vi.mock('@/components/ui/sidebar', () => ({
  Sidebar: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar">{children}</div>
  ),
  SidebarContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar-content">{children}</div>
  ),
  SidebarGroup: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar-group">{children}</div>
  ),
  SidebarGroupContent: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar-group-content">{children}</div>
  ),
  SidebarGroupLabel: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar-group-label">{children}</div>
  ),
  SidebarMenu: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar-menu">{children}</div>
  ),
  SidebarMenuButton: ({ children, asChild, onClick }: { children: React.ReactNode; asChild?: boolean; onClick?: () => void }) => 
    asChild ? <div>{children}</div> : <button onClick={onClick}>{children}</button>,
  SidebarMenuItem: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar-menu-item">{children}</div>
  ),
  SidebarHeader: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar-header">{children}</div>
  ),
  SidebarFooter: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar-footer">{children}</div>
  ),
}))

test('renders AppSidebar with navigation items', () => {
  render(
    <BrowserRouter>
      <AppSidebar />
    </BrowserRouter>
  )

  expect(screen.getByText('AquaCharge')).toBeInTheDocument()
  expect(screen.getByText('Home')).toBeInTheDocument()
  expect(screen.getByText('Stations')).toBeInTheDocument()
  expect(screen.getByText('Vessels')).toBeInTheDocument()
})

test('renders user section with default values when no user', () => {
  render(
    <BrowserRouter>
      <AppSidebar />
    </BrowserRouter>
  )

  expect(screen.getByText('Demo User')).toBeInTheDocument()
  expect(screen.getByText('demo@aquacharge.com')).toBeInTheDocument()
  expect(screen.getByText('Sign Out')).toBeInTheDocument()
})