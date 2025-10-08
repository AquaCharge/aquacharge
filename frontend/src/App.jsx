import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { AppSidebar } from '@/components/layout/app-sidebar'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import Home from './pages/Home'
import Stations from './pages/Stations'
import Vessels from './pages/Vessels'

export default function App() {
  return (
    <Router>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <main className="flex-1 p-2">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/stations" element={<Stations />} />
              <Route path="/vessels" element={<Vessels />} />
            </Routes>
          </main>
        </SidebarInset>
      </SidebarProvider>
    </Router>
  )
}