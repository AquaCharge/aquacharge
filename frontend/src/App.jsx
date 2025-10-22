import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AppSidebar } from '@/components/layout/app-sidebar'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import Home from './pages/Home'
import Stations from './pages/Stations'
import Vessels from './pages/Vessels'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'

// Loading component
const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-cyan-50">
    <div className="text-center">
      <div className="mx-auto w-16 h-16 bg-gradient-to-br from-blue-600 to-cyan-600 rounded-2xl flex items-center justify-center mb-4">
        <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
      </div>
      <p className="text-gray-600">Loading AquaCharge...</p>
    </div>
  </div>
)

// Protected routes component
const ProtectedRoutes = () => {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <main className="flex-1 p-2">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/stations" element={<Stations />} />
            <Route path="/vessels" element={<Vessels />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

// Auth routes component
const AuthRoutes = () => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}

// Main app content
const AppContent = () => {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <LoadingSpinner />
  }

  return isAuthenticated ? <ProtectedRoutes /> : <AuthRoutes />
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <AppContent />
      </Router>
    </AuthProvider>
  )
}