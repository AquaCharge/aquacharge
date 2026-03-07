import { useEffect, useMemo, useState } from 'react'
import { Activity, Gauge, MapPin, RefreshCw, Ship, Zap } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { getApiEndpoint } from '@/config/api'
import { useAuth } from '@/contexts/AuthContext'

const POLL_INTERVAL_MS = 10_000
const PERIOD_OPTIONS = [
  { value: '1', label: 'Last hour' },
  { value: '6', label: 'Last 6 hours' },
  { value: '24', label: 'Last 24 hours' },
  { value: '72', label: 'Last 72 hours' },
]

const STATUS_TONES = {
  Created: 'bg-slate-100 text-slate-800',
  Dispatched: 'bg-sky-100 text-sky-800',
  Accepted: 'bg-indigo-100 text-indigo-800',
  Committed: 'bg-amber-100 text-amber-900',
  Active: 'bg-emerald-100 text-emerald-900',
  Completed: 'bg-blue-100 text-blue-900',
  Settled: 'bg-violet-100 text-violet-900',
  Archived: 'bg-neutral-100 text-neutral-700',
  Cancelled: 'bg-rose-100 text-rose-900',
}

const formatNumber = (value, fractionDigits = 1) =>
  new Intl.NumberFormat(undefined, {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  }).format(Number(value || 0))

const formatTimestamp = (value) => {
  if (!value) return 'No telemetry yet'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'No telemetry yet'
  return date.toLocaleString()
}

const buildPath = (points, width, height) => {
  if (points.length === 0) return ''
  const maxValue = Math.max(...points.map((point) => point.v2gContributionKw), 1)
  return points
    .map((point, index) => {
      const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width
      const y = height - (point.v2gContributionKw / maxValue) * height
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')
}

const MetricCard = ({ title, value, helper, icon: Icon, loading }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      <Icon className="h-4 w-4 text-muted-foreground" />
    </CardHeader>
    <CardContent>
      {loading ? <Skeleton className="h-8 w-24" /> : <div className="text-2xl font-bold">{value}</div>}
      <p className="text-xs text-muted-foreground">{helper}</p>
    </CardContent>
  </Card>
)

const PowerDashboard = () => {
  const { user } = useAuth()
  const [filters, setFilters] = useState({
    eventId: '',
    region: '',
    periodHours: '24',
  })
  const [snapshot, setSnapshot] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const authToken = localStorage.getItem('auth-token')
  const canViewDashboard = user?.type_name === 'POWER_OPERATOR'

  const queryString = useMemo(() => {
    const params = new URLSearchParams()
    if (filters.eventId) params.set('eventId', filters.eventId)
    if (filters.region.trim()) params.set('region', filters.region.trim())
    params.set('periodHours', filters.periodHours)
    return params.toString()
  }, [filters])

  const loadDashboard = async () => {
    if (!authToken) {
      setError('Missing authentication token.')
      setIsLoading(false)
      return
    }

    setError('')
    try {
      const response = await fetch(getApiEndpoint(`/api/drevents/monitoring?${queryString}`), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || payload.details || 'Failed to load monitoring dashboard')
      }

      const payload = await response.json()
      setSnapshot(payload)

      if (!filters.eventId && payload.filters?.eventId) {
        setFilters((current) => ({
          ...current,
          eventId: payload.filters.eventId,
        }))
      }
    } catch (loadError) {
      setError(loadError.message || 'Failed to load monitoring dashboard.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!canViewDashboard) {
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    loadDashboard()
    const timer = window.setInterval(loadDashboard, POLL_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [canViewDashboard, queryString])

  const selectedEvent = snapshot?.selectedEvent
  const summary = snapshot?.summary || {}
  const loadCurve = snapshot?.loadCurve || []
  const vesselRates = snapshot?.vesselRates || []
  const availableEvents = snapshot?.availableEvents || []
  const chartPath = buildPath(loadCurve, 540, 180)
  const maxCurveValue = loadCurve.length
    ? Math.max(...loadCurve.map((point) => point.v2gContributionKw), 0)
    : 0

  if (!canViewDashboard) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Gauge className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Access Denied</h3>
          <p className="text-gray-600">Only power operator accounts can access the DR monitoring dashboard.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">DR Monitoring Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Real-time visibility into dispatch progress, vessel discharge rates, and event telemetry.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={() => {
          setIsLoading(true)
          loadDashboard()
        }}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Filters</CardTitle>
          <CardDescription>Dashboard refreshes automatically every 10 seconds.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="eventId">DR Event</Label>
            <select
              id="eventId"
              className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
              value={filters.eventId}
              onChange={(event) => setFilters((current) => ({ ...current, eventId: event.target.value }))}
            >
              <option value="">Latest matching event</option>
              {availableEvents.map((event) => (
                <option key={event.id} value={event.id}>
                  {event.id} · {event.status} · {event.regionLabel || event.stationId}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="periodHours">Time Period</Label>
            <select
              id="periodHours"
              className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
              value={filters.periodHours}
              onChange={(event) => setFilters((current) => ({ ...current, periodHours: event.target.value }))}
            >
              {PERIOD_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="region">Geographic Region</Label>
            <Input
              id="region"
              placeholder="City, province/state, or country"
              value={filters.region}
              onChange={(event) => setFilters((current) => ({ ...current, region: event.target.value }))}
            />
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Total Energy Delivered"
          value={`${formatNumber(summary.totalEnergyDeliveredKwh || 0)} kWh`}
          helper={selectedEvent ? `Target ${formatNumber(summary.targetEnergyKwh || 0)} kWh` : 'Select a DR event to monitor'}
          icon={Zap}
          loading={isLoading}
        />
        <MetricCard
          title="Progress Toward Goal"
          value={`${formatNumber(summary.progressPercent || 0)}%`}
          helper="Computed from event target energy and recorded telemetry"
          icon={Activity}
          loading={isLoading}
        />
        <MetricCard
          title="Active Vessels"
          value={String(summary.activeVessels || 0)}
          helper="Latest vessel telemetry in the selected time window"
          icon={Ship}
          loading={isLoading}
        />
        <MetricCard
          title="Event Status"
          value={summary.eventStatus || 'No event selected'}
          helper={selectedEvent?.regionLabel || 'Filter by event or region'}
          icon={Gauge}
          loading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Selected Event
            </CardTitle>
            <CardDescription>Lifecycle state and station context for the monitored event.</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-6 w-40" />
                <Skeleton className="h-20 w-full" />
              </div>
            ) : selectedEvent ? (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="font-mono text-sm text-gray-600">{selectedEvent.id}</span>
                  <Badge className={STATUS_TONES[selectedEvent.status] || STATUS_TONES.Created}>
                    {selectedEvent.status}
                  </Badge>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-lg border bg-slate-50 p-4">
                    <div className="text-sm text-slate-500">Dispatch Window</div>
                    <div className="mt-2 font-medium text-slate-900">{formatTimestamp(selectedEvent.startTime)}</div>
                    <div className="text-sm text-slate-600">to {formatTimestamp(selectedEvent.endTime)}</div>
                  </div>
                  <div className="rounded-lg border bg-slate-50 p-4">
                    <div className="text-sm text-slate-500">Region</div>
                    <div className="mt-2 flex items-center gap-2 font-medium text-slate-900">
                      <MapPin className="h-4 w-4 text-slate-500" />
                      {selectedEvent.regionLabel || selectedEvent.stationId}
                    </div>
                    <div className="text-sm text-slate-600">Station {selectedEvent.stationId}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed p-6 text-sm text-slate-600">
                No DR event matched the current filters.
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>V2G Contribution Curve</CardTitle>
            <CardDescription>
              Measurement-backed vessel contribution over time. Baseline grid load is not yet available in the current schema.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : loadCurve.length ? (
              <div className="space-y-3">
                <svg
                  viewBox="0 0 560 220"
                  className="h-64 w-full rounded-lg border bg-gradient-to-br from-slate-50 to-white"
                  role="img"
                  aria-label="V2G contribution curve"
                >
                  <defs>
                    <linearGradient id="curve-fill" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#0f766e" stopOpacity="0.22" />
                      <stop offset="100%" stopColor="#0f766e" stopOpacity="0.04" />
                    </linearGradient>
                  </defs>
                  <line x1="10" y1="190" x2="550" y2="190" stroke="#cbd5e1" strokeWidth="1" />
                  <line x1="10" y1="20" x2="10" y2="190" stroke="#cbd5e1" strokeWidth="1" />
                  {chartPath ? <path d={`${chartPath} L 540 180 L 20 180 Z`} fill="url(#curve-fill)" transform="translate(10,10)" /> : null}
                  {chartPath ? (
                    <path
                      d={chartPath}
                      transform="translate(10,10)"
                      fill="none"
                      stroke="#0f766e"
                      strokeWidth="3"
                      strokeLinejoin="round"
                      strokeLinecap="round"
                    />
                  ) : null}
                  {loadCurve.map((point, index) => {
                    const x = loadCurve.length === 1 ? 280 : 10 + (index / (loadCurve.length - 1)) * 540
                    const y = 190 - (point.v2gContributionKw / Math.max(maxCurveValue, 1)) * 170
                    return <circle key={point.timestamp} cx={x} cy={y} r="3.5" fill="#0f766e" />
                  })}
                  <text x="18" y="18" fill="#475569" fontSize="12">
                    Peak {formatNumber(maxCurveValue || 0)} kW
                  </text>
                  <text x="18" y="208" fill="#64748b" fontSize="12">
                    {loadCurve[0] ? new Date(loadCurve[0].timestamp).toLocaleTimeString() : ''}
                  </text>
                  <text x="458" y="208" fill="#64748b" fontSize="12">
                    {loadCurve.at(-1) ? new Date(loadCurve.at(-1).timestamp).toLocaleTimeString() : ''}
                  </text>
                </svg>
                <p className="text-xs text-slate-500">
                  {snapshot?.baselineAvailable
                    ? 'Baseline grid load data is included.'
                    : 'Baseline grid load is unavailable in the current telemetry model, so this chart shows V2G contribution only.'}
                </p>
              </div>
            ) : (
              <div className="rounded-lg border border-dashed p-6 text-sm text-slate-600">
                No telemetry has been recorded in the selected time window.
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Individual Vessel Discharge Rates</CardTitle>
          <CardDescription>Latest telemetry for each participating vessel in the selected window.</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((row) => (
                <Skeleton key={row} className="h-16 w-full" />
              ))}
            </div>
          ) : vesselRates.length ? (
            <div className="space-y-3">
              {vesselRates.map((vessel) => (
                <div
                  key={vessel.vesselId}
                  className="flex flex-col gap-3 rounded-lg border p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div>
                    <div className="font-medium text-slate-900">{vessel.vesselId}</div>
                    <div className="text-sm text-slate-600">Contract {vessel.contractId || 'unlinked'} · {formatTimestamp(vessel.timestamp)}</div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 md:w-80">
                    <div>
                      <div className="text-xs uppercase tracking-wide text-slate-500">Discharge Rate</div>
                      <div className="font-semibold text-slate-900">{formatNumber(vessel.dischargeRateKw, 2)} kW</div>
                    </div>
                    <div>
                      <div className="text-xs uppercase tracking-wide text-slate-500">Current SOC</div>
                      <div className="font-semibold text-slate-900">{formatNumber(vessel.currentSoc, 1)}%</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed p-6 text-sm text-slate-600">
              No vessel discharge measurements matched the current filters.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default PowerDashboard
