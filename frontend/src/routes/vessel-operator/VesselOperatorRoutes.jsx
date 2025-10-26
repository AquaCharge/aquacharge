import { Routes, Route, Navigate } from 'react-router-dom'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import { VesselOperatorSidebar } from './VesselOperatorSidebar'

// Vessel Operator specific pages
import VesselDashboard from '../../pages/vessel-operator/VesselDashboard'
import MyBookings from '../../pages/vessel-operator/MyBookings'
import FindChargers from '../../pages/vessel-operator/FindChargers'

// Import shared pages
import Stations from '../../pages/Stations'
import Vessels from '../../pages/Vessels'

const VesselOperatorRoutes = () => {
  return (
    <SidebarProvider>
      <VesselOperatorSidebar />
      <SidebarInset>
        <main className="flex-1 p-6 lg:p-8">
          <Routes>
            <Route path="/" element={<VesselDashboard />} />
            <Route path="/find-chargers" element={<FindChargers />} />
            <Route path="/my-bookings" element={<MyBookings />} />
            <Route path="/my-vessels" element={<Vessels />} />
            <Route path="/stations" element={<Stations />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default VesselOperatorRoutes