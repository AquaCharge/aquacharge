import { Routes, Route, Navigate } from 'react-router-dom'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { PowerOperatorSidebar } from './PowerOperatorSidebar'

// Power Operator specific pages
import PowerDashboard from '../../pages/power-operator/PowerDashboard'
import ContractsManagement from '../../pages/power-operator/ContractsManagement'
import Analytics from '../../pages/power-operator/Analytics'
import UserManagement from '../../pages/power-operator/UserManagement'
import DemandResponse from '../../pages/power-operator/DemandResponse'

// Import shared pages
import Profile from '../../pages/Profile'

const PowerOperatorRoutes = () => {
  return (
    <SidebarProvider>
      <PowerOperatorSidebar />
      <SidebarInset>
        <main className="flex-1 p-6 lg:p-8">
          <Routes>
            <Route path="/" element={<PowerDashboard />} />
            <Route path="/contracts" element={<ContractsManagement />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/users" element={<UserManagement />} />
            <Route path="/demand-response" element={<DemandResponse />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default PowerOperatorRoutes