import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import VesselOperatorRoutes from './routes/vessel-operator/VesselOperatorRoutes'
import PowerOperatorRoutes from './routes/power-operator/PowerOperatorRoutes'
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

// Protected routes component - Routes based on user type
const ProtectedRoutes = () => {
  const { user } = useAuth()
  
  // Route users to appropriate application view based on their type
  if (user?.type_name === 'POWER_OPERATOR') {
    return <PowerOperatorRoutes />
  }
  
  // Default to vessel operator view (includes VESSEL_OPERATOR and fallback)
  return <VesselOperatorRoutes />
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