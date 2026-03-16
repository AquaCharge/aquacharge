import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { MetricCard, StateOfChargeCard, WeeklyEarningsCard, AllTimeCard } from '@/components/ui/DashboardCards'
import { Ship, Calendar, Zap } from 'lucide-react'
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

const HISTORY_STATUSES = ['completed', 'failed', 'cancelled']

const formatContractDate = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

const formatDuration = (startIso, endIso) => {
  if (!startIso || !endIso) return '—'
  const start = new Date(startIso).getTime()
  const end = new Date(endIso).getTime()
  const ms = end - start
  if (ms <= 0) return '—'
  const totalMinutes = Math.floor(ms / 60_000)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

const formatAmount = (value) =>
  typeof value === 'number' ? `$${Number(value).toFixed(2)}` : '—'

const historyStatusBadgeClass = (status) => {
  switch (status) {
    case 'completed':
      return 'bg-emerald-100 text-emerald-800'
    case 'failed':
      return 'bg-red-100 text-red-800'
    case 'cancelled':
      return 'bg-gray-100 text-gray-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const VesselDashboard = () => {
  const { user, refreshUser } = useAuth()
  const [dashboard, setDashboard] = useState(null)
  const [vessels, setVessels] = useState([])
  const [myContracts, setMyContracts] = useState([])
  const [contractsHistoryLoading, setContractsHistoryLoading] = useState(true)
  const [historyStatusFilter, setHistoryStatusFilter] = useState('all')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [vesselSelectLoading, setVesselSelectLoading] = useState(false)
  const contractsHistoryLoadedOnce = useRef(false)

  const authToken = localStorage.getItem('auth-token')
  const userId = user?.id
  const sampleWeeklyEarnings = {
    total: 1238.65,
    dailyEarnings: [128, 320.5, 362, 284.15, 421, 0, 0],
    todayIndex: 4,  // 0=Mon, 6=Sun; e.g. 4 = Friday
  }
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

  const loadMyContracts = async () => {
    if (!authToken) {
      setContractsHistoryLoading(false)
      return
    }
    const isFirstLoad = !contractsHistoryLoadedOnce.current
    if (isFirstLoad) setContractsHistoryLoading(true)
    try {
      const response = await fetch(getApiEndpoint('/api/contracts/my-contracts'), {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || 'Failed to load contracts')
      }
      const raw = await response.json()
      const nextList = Array.isArray(raw) ? raw : []
      setMyContracts((prev) => {
        if (prev.length !== nextList.length) return nextList
        const byId = (a, b) => (a.id || '').localeCompare(b.id || '')
        const prevSorted = [...prev].sort(byId)
        const nextSorted = [...nextList].sort(byId)
        const same = nextSorted.every(
          (c, i) => c.id === prevSorted[i].id && c.updatedAt === prevSorted[i].updatedAt
        )
        return same ? prev : nextList
      })
      contractsHistoryLoadedOnce.current = true
    } catch (err) {
      console.error('Failed to load contract history', err)
      setMyContracts([])
      contractsHistoryLoadedOnce.current = true
    } finally {
      if (isFirstLoad) setContractsHistoryLoading(false)
    }
  }

  const contractsHistory = myContracts
    .filter((c) => HISTORY_STATUSES.includes(c.status))
    .sort((a, b) => {
      const aEnd = a.endTime ? new Date(a.endTime).getTime() : 0
      const bEnd = b.endTime ? new Date(b.endTime).getTime() : 0
      return bEnd - aEnd
    })

  useEffect(() => {
    loadDashboard()
    const timer = window.setInterval(loadDashboard, POLL_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [authToken])

  useEffect(() => {
    loadMyContracts()
    const timer = window.setInterval(loadMyContracts, POLL_INTERVAL_MS)
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
    <div className="space-y-2">
      <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
        <div className="mb-4">
          <h1 className="text-3xl font-bold text-gray-900">Vessel Operator Dashboard</h1>
          <p className="text-gray-600 mt-2">
            Welcome to your AquaCharge vessel management center
          </p>
        </div>
        <div className="flex items-center gap-1">
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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2">
        <StateOfChargeCard
          percent={currentVessel?.socPercent}
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
          loading={isLoading}
        />
        <MetricCard
          title="Time remaining"
          value={formatTimeRemaining(activeContract?.timeRemainingSeconds)}
          helper="Active contract"
          loading={isLoading}
        />
      </div>

      {/* All time stats + weekly earnings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        <AllTimeCard metrics={metrics} loading={isLoading} />
        <WeeklyEarningsCard
          weeklyEarnings={dashboard?.weeklyEarnings}
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
            <div className="grid grid-cols-2 gap-2 text-sm">
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
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks for vessel operators</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <Link
                to="/find-stations"
                className="block w-full p-3 text-left border rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <Ship className="h-5 w-5 text-black" />
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
                  <Calendar className="h-5 w-5 text-black" />
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
                  <Ship className="h-5 w-5 text-black" />
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
                  <Zap className="h-5 w-5 text-black" />
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

      {/* Contracts History */}
      <Card className="mt-4">
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <CardTitle className="text-lg font-semibold text-gray-900">
            Contracts History
          </CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Status
            </span>
            <select
              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground shadow-sm"
              value={historyStatusFilter}
              onChange={(event) => setHistoryStatusFilter(event.target.value)}
            >
              <option value="all">All</option>
              <option value="completed">Completed</option>
              <option value="failed">Failed</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {contractsHistoryLoading ? (
            <div className="p-1">
              <Skeleton className="h-8 w-full mb-2" />
              <Skeleton className="h-10 w-full mb-1" />
              <Skeleton className="h-10 w-full mb-1" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : contractsHistory.length === 0 ? (
            <div className="p-6 text-center text-sm text-muted-foreground">
              No contract history yet
            </div>
          ) : (
            <div className="-mx-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="text-left font-medium text-gray-700 px-4 py-3">Vessel</th>
                    <th className="text-left font-medium text-gray-700 px-4 py-3">Date</th>
                    <th className="text-left font-medium text-gray-700 px-4 py-3">Status</th>
                    <th className="text-left font-medium text-gray-700 px-4 py-3">Duration</th>
                    <th className="text-left font-medium text-gray-700 px-4 py-3">Energy</th>
                    <th className="text-right font-medium text-gray-700 px-4 py-3">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {contractsHistory
                    .filter((c) =>
                      historyStatusFilter === 'all' ? true : c.status === historyStatusFilter
                    )
                    .map((c) => (
                      <tr
                        key={c.id}
                        className="border-b last:border-b-0 hover:bg-muted/30 transition-colors"
                      >
                        <td className="px-4 py-3 text-left">{c.vesselName || '—'}</td>
                        <td className="px-4 py-3 text-left">{formatContractDate(c.endTime)}</td>
                        <td className="px-4 py-3">
                          <Badge
                            className={`${historyStatusBadgeClass(
                              c.status
                            )} font-normal capitalize`}
                          >
                            {c.status.toUpperCase()}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-left">
                          {formatDuration(c.startTime, c.endTime)}
                        </td>
                        <td className="px-4 py-3 text-left">
                          {c.energyAmount != null
                            ? `${Number(c.energyAmount).toFixed(1)} kWh`
                            : '—'}
                        </td>
                        <td className="px-4 py-3 text-right font-medium">
                          {formatAmount(c.totalValue)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default VesselDashboard
