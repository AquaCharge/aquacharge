import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Ship, Calendar, Zap, DollarSign, Clock, Battery, Activity } from 'lucide-react'
import { getApiEndpoint } from '@/config/api'
import { useAuth } from '@/contexts/AuthContext'

const POLL_INTERVAL_MS = 10_000

const formatTimeRemaining = (seconds) => {
  if (seconds == null || seconds <= 0) return '—'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  if (m >= 60) {
    const h = Math.floor(m / 60)
    return `${h}h ${m % 60}m left`
  }
  return `${m}:${String(s).padStart(2, '0')} left`
}

const MetricCard = ({ title, value, helper, icon: Icon, loading }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      <Icon className="h-4 w-4 text-muted-foreground" />
    </CardHeader>
    <CardContent>
      {loading ? (
        <Skeleton className="h-8 w-24" />
      ) : (
        <div className="text-2xl font-bold">{value}</div>
      )}
      <p className="text-xs text-muted-foreground">{helper}</p>
    </CardContent>
  </Card>
)

const VesselDashboard = () => {
  const { user, refreshUser } = useAuth()
  const [dashboard, setDashboard] = useState(null)
  const [vessels, setVessels] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [vesselSelectLoading, setVesselSelectLoading] = useState(false)

  const authToken = localStorage.getItem('auth-token')
  const userId = user?.id

  const loadDashboard = async () => {
    if (!authToken) {
      setError('Missing authentication token.')
      setIsLoading(false)
      return
    }
    setError('')
    try {
      const response = await fetch(getApiEndpoint('/api/vo/dashboard'), {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || payload.details || 'Failed to load dashboard')
      }
      const data = await response.json()
      setDashboard(data)
      console.log(data)
      // If backend auto-set first vessel but auth context doesn't have it yet, refresh user
      if (data?.currentVessel && !user?.currentVesselId && refreshUser) {
        refreshUser()
      }
    } catch (e) {
      setError(e.message || 'Failed to load dashboard.')
    } finally {
      setIsLoading(false)
    }
  }

  const loadVessels = async () => {
    if (!authToken || !userId) return
    try {
      const response = await fetch(
        getApiEndpoint(`/api/vessels?userId=${encodeURIComponent(userId)}`),
        { headers: { Authorization: `Bearer ${authToken}` } }
      )
      if (response.ok) {
        const list = await response.json()
        setVessels(Array.isArray(list) ? list : [])
      }
    } catch (err) {
      console.error('Failed to load vessels', err)
    }
  }

  useEffect(() => {
    loadDashboard()
    const timer = window.setInterval(loadDashboard, POLL_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [authToken])

  useEffect(() => {
    if (userId) loadVessels()
  }, [userId])

  const setCurrentVessel = async (vesselId) => {
    if (!authToken) return
    setVesselSelectLoading(true)
    try {
      const response = await fetch(getApiEndpoint('/api/auth/me'), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          currentVesselId: vesselId === '' || vesselId == null ? null : vesselId,
        }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || 'Failed to set current vessel')
      }
      await refreshUser()
      await loadDashboard()
    } catch (e) {
      setError(e.message)
    } finally {
      setVesselSelectLoading(false)
    }
  }

  const currentVessel = dashboard?.currentVessel ?? null
  const activeContract = dashboard?.activeContract ?? null
  const metrics = dashboard?.metrics ?? {
    contractsCompleted: 0,
    totalKwhDischarged: 0,
    totalEarnings: 0,
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Vessel Operator Dashboard</h1>
          <p className="text-gray-600 mt-2">
            Welcome to your AquaCharge vessel management center
          </p>
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-muted-foreground">Current vessel</label>
          <select
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={user?.currentVesselId ?? ''}
            onChange={(e) => setCurrentVessel(e.target.value || null)}
            disabled={vesselSelectLoading}
          >
            <option value="">— Select vessel —</option>
            {vessels.map((v) => (
              <option key={v.id} value={v.id}>
                {v.displayName || v.id}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <Card className="border-destructive bg-destructive/5">
          <CardContent className="pt-4">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {!currentVessel && vessels.length > 0 && (
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="pt-4">
            <p className="text-sm text-amber-800">
              Select a vessel above to see live metrics (SoC, discharge rate, time remaining).
            </p>
          </CardContent>
        </Card>
      )}

      {/* Quick Stats: current vessel + metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Current vessel SoC"
          value={currentVessel?.socPercent != null ? `${currentVessel.socPercent}%` : '—'}
          helper="State of charge"
          icon={Battery}
          loading={isLoading}
        />
        <MetricCard
          title="Discharge rate"
          value={
            currentVessel?.dischargeRateKw != null
              ? `${Number(currentVessel.dischargeRateKw).toFixed(1)} kW`
              : '—'
          }
          helper="Max discharge rate"
          icon={Zap}
          loading={isLoading}
        />
        <MetricCard
          title="Time remaining"
          value={formatTimeRemaining(activeContract?.timeRemainingSeconds)}
          helper="Active contract"
          icon={Clock}
          loading={isLoading}
        />
        <MetricCard
          title="Estimated earnings"
          value={
            activeContract?.estimatedEarnings != null
              ? `$${Number(activeContract.estimatedEarnings).toFixed(2)}`
              : metrics.totalEarnings != null
                ? `$${Number(metrics.totalEarnings).toFixed(2)} total`
                : '—'
          }
          helper="From active contract or total"
          icon={DollarSign}
          loading={isLoading}
        />
      </div>

      {/* Real metrics: contracts completed, total kW, earnings */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <MetricCard
          title="Contracts completed"
          value={metrics.contractsCompleted ?? 0}
          helper="All time"
          icon={Ship}
          loading={isLoading}
        />
        <MetricCard
          title="Total kW discharged"
          value={
            metrics.totalKwhDischarged != null
              ? Number(metrics.totalKwhDischarged).toFixed(1)
              : '0'
          }
          helper="kWh delivered"
          icon={Activity}
          loading={isLoading}
        />
        <MetricCard
          title="Earnings"
          value={
            metrics.totalEarnings != null
              ? `$${Number(metrics.totalEarnings).toFixed(2)}`
              : '$0.00'
          }
          helper="From completed contracts"
          icon={DollarSign}
          loading={isLoading}
        />
      </div>

      {/* Active contract card */}
      {activeContract && (
        <Card>
          <CardHeader>
            <CardTitle>Active contract</CardTitle>
            <CardDescription>
              Ends {activeContract.endTime ? new Date(activeContract.endTime).toLocaleString() : '—'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Energy (this contract)</p>
                <p className="font-semibold">{Number(activeContract.energyAmountKwh ?? 0).toFixed(1)} kWh</p>
              </div>
              <div>
                <p className="text-muted-foreground">Earnings (this contract)</p>
                <p className="font-semibold">${Number(activeContract.estimatedEarnings ?? 0).toFixed(2)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions with links */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks for vessel operators</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Link
                to="/find-stations"
                className="block w-full p-3 text-left border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <Ship className="h-5 w-5 text-blue-600" />
                  <div>
                    <p className="font-medium">Find Charging Station</p>
                    <p className="text-sm text-gray-600">Locate nearby chargers</p>
                  </div>
                </div>
              </Link>
              <Link
                to="/my-bookings"
                className="block w-full p-3 text-left border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <Calendar className="h-5 w-5 text-green-600" />
                  <div>
                    <p className="font-medium">My Bookings</p>
                    <p className="text-sm text-gray-600">View and manage reservations</p>
                  </div>
                </div>
              </Link>
              <Link
                to="/my-vessels"
                className="block w-full p-3 text-left border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <Ship className="h-5 w-5 text-purple-600" />
                  <div>
                    <p className="font-medium">Manage Vessels</p>
                    <p className="text-sm text-gray-600">Add or edit vessel information</p>
                  </div>
                </div>
              </Link>
              <Link
                to="/my-contracts"
                className="block w-full p-3 text-left border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <Zap className="h-5 w-5 text-amber-600" />
                  <div>
                    <p className="font-medium">My Contracts</p>
                    <p className="text-sm text-gray-600">Review and accept DR contracts</p>
                  </div>
                </div>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Last updated</CardTitle>
            <CardDescription>
              Dashboard refreshes every 10–15 seconds
            </CardDescription>
          </CardHeader>
          <CardContent>
            {dashboard?.updatedAt ? (
              <p className="text-sm text-muted-foreground">
                {new Date(dashboard.updatedAt).toLocaleString()}
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">—</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default VesselDashboard
