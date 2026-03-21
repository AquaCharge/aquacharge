import { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  Gauge,
  LineChart,
  RefreshCw,
  Ship,
  Timer,
  Zap,
} from 'lucide-react'

import { MetricCard as DashboardMetricCard } from '@/components/ui/DashboardCards'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { getApiEndpoint } from '@/config/api'
import { useAuth } from '@/contexts/AuthContext'
import { cn } from '@/lib/utils'

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

const selectClassName =
  'h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

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

const formatDateRange = (start, end) => {
  if (!start || !end) return 'No dispatch window'
  return `${formatTimestamp(start)} to ${formatTimestamp(end)}`
}

const clampPercent = (value) => Math.max(0, Math.min(100, Number(value || 0)))

const getSeriesValue = (point) =>
  Number(
    point?.cumulativeEnergyDischargedKwh
      ?? point?.energyDischargedKwh
      ?? point?.v2gContributionKw
      ?? 0
  )

const buildPath = (points, width, height) => {
  if (points.length === 0) return ''
  const maxValue = Math.max(...points.map(getSeriesValue), 1)
  return points
    .map((point, index) => {
      const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width
      const y = height - (getSeriesValue(point) / maxValue) * height
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')
}

const getCurveBounds = (points) => {
  const maxValue = points.length ? Math.max(...points.map(getSeriesValue), 0) : 0
  const minValue = points.length ? Math.min(...points.map(getSeriesValue), 0) : 0
  return {
    maxValue,
    minValue: Math.min(minValue, 0),
    valueRange: Math.max(maxValue - Math.min(minValue, 0), 1),
  }
}

const getPointCoordinates = (point, pointIndex, points, width, height, minValue, valueRange) => {
  const x = points.length === 1 ? width / 2 : (pointIndex / (points.length - 1)) * width
  const normalizedValue = (getSeriesValue(point) - minValue) / valueRange
  const y = height - normalizedValue * height
  return { x, y }
}

const getTickValues = (maxValue, minValue) => {
  const top = Math.max(maxValue, 0)
  const bottom = Math.min(minValue, 0)
  const mid = bottom + (top - bottom) / 2
  return [top, mid, bottom]
}

const DashboardKeyStat = ({ label, value, secondary }) => (
  <div>
    <p className="mb-2 text-xs uppercase tracking-wide text-muted-foreground">{label}</p>
    <p className="text-lg font-semibold tabular-nums text-foreground">{value}</p>
    {secondary ? <p className="text-sm text-muted-foreground">{secondary}</p> : null}
  </div>
)

const EventSummaryCard = ({ selectedEvent, summary, loading }) => {
  const targetEnergy = Number(summary.targetEnergyKwh ?? selectedEvent?.targetEnergyKwh ?? 0)
  const progressPercent = clampPercent(summary.progressPercent)

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="mb-4 flex items-center gap-2 text-md font-light">
          {selectedEvent?.status === 'Active' ? (
            <span className="relative flex h-2.5 w-2.5 shrink-0">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75 [animation-duration:3s]" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-600" />
            </span>
          ) : (
            <Activity className="h-4 w-4 text-muted-foreground" />
          )}
          Dispatch Overview
        </CardTitle>
        {loading ? (
          <div className="space-y-4">
            <Skeleton className="h-6 w-32" />
            <div className="grid gap-6 sm:grid-cols-2">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
            <Skeleton className="h-3 w-full rounded-full" />
          </div>
        ) : selectedEvent ? (
          <>
            <div className="flex flex-wrap items-center gap-3">
              <span className="font-mono text-sm text-muted-foreground">{selectedEvent.id}</span>
              <Badge className={STATUS_TONES[selectedEvent.status] || STATUS_TONES.Created}>
                {selectedEvent.status}
              </Badge>
            </div>
            <div className="mt-4 grid gap-6 sm:grid-cols-2">
              <div>
                <div className="mb-1 text-4xl font-medium tabular-nums">
                  {formatNumber(summary.totalEnergyDeliveredKwh || 0)} kWh
                </div>
                <p className="text-xs text-muted-foreground">Energy delivered</p>
              </div>
              <div>
                <div className="mb-1 text-4xl font-medium tabular-nums">
                  {formatNumber(progressPercent, 0)}%
                </div>
                <p className="text-xs text-muted-foreground">Progress toward target</p>
              </div>
            </div>
            <div className="mt-6">
              <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-400/70 to-teal-600 transition-all duration-500 ease-out"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              <div className="mt-1 flex justify-end text-xs text-muted-foreground">
                <span>{formatNumber(targetEnergy, 1)} kWh target</span>
              </div>
            </div>
          </>
        ) : (
          <div className="rounded-md border border-dashed border-muted px-4 py-8 text-center text-sm text-muted-foreground">
            No DR event matched the current filters.
          </div>
        )}
      </CardHeader>
      <CardContent>
        <hr className="my-4" />
        {loading ? (
          <div className="grid gap-4 sm:grid-cols-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        ) : selectedEvent ? (
          <div className="flex w-full flex-row flex-wrap justify-between gap-6">
            <DashboardKeyStat
              label="Region"
              value={selectedEvent.regionLabel || selectedEvent.stationId}
              secondary={`Station ${selectedEvent.stationId}`}
            />
            <DashboardKeyStat
              label="Active vessels"
              value={String(summary.activeVessels || 0)}
              secondary="Latest telemetry in the selected window"
            />
            <DashboardKeyStat
              label="Dispatch window"
              value={formatTimestamp(selectedEvent.startTime)}
              secondary={formatTimestamp(selectedEvent.endTime)}
            />
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">Apply filters or select an event to populate dispatch details.</div>
        )}
      </CardContent>
    </Card>
  )
}

const EventDetailsCard = ({ selectedEvent, summary, loading }) => (
  <Card className="h-full">
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
      <CardTitle className="text-md font-light">
        {selectedEvent?.id || 'Selected Event'}
      </CardTitle>
    </CardHeader>
    <CardContent>
      {loading ? (
        <>
          <Skeleton className="mb-4 h-6 w-32" />
          <div className="space-y-2">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </>
      ) : !selectedEvent ? (
        <div className="flex h-[220px] items-center justify-center rounded-md border border-dashed border-muted px-4 text-center text-xs text-muted-foreground">
          Select a DR event to see lifecycle and location details.
        </div>
      ) : (
        <div className="space-y-4">
          <div className="space-y-2">
            {[
              { label: 'Event status', value: summary.eventStatus || selectedEvent.status || '—' },
              { label: 'Region', value: selectedEvent.regionLabel || '—' },
              { label: 'Station', value: selectedEvent.stationId || '—' },
              { label: 'Dispatch start', value: formatTimestamp(selectedEvent.startTime) },
              { label: 'Dispatch end', value: formatTimestamp(selectedEvent.endTime) },
              {
                label: 'Target energy',
                value: `${formatNumber(summary.targetEnergyKwh ?? selectedEvent.targetEnergyKwh ?? 0, 1)} kWh`,
              },
            ].map((item, index) => (
              <div key={item.label}>
                <div className="flex items-start justify-between gap-4 p-3">
                  <p className="text-xs text-muted-foreground">{item.label}</p>
                  <p className="text-right text-sm font-semibold text-foreground">{item.value}</p>
                </div>
                {index < 5 ? <hr /> : null}
              </div>
            ))}
          </div>
        </div>
      )}
    </CardContent>
  </Card>
)

const VesselTelemetryCard = ({ vesselRates, loading }) => (
  <Card className="h-full">
    <CardHeader>
      <CardTitle className="mb-4 flex items-center gap-2 text-md font-light">
        <Ship className="h-4 w-4 text-muted-foreground" />
        Vessel Telemetry
      </CardTitle>
      <p className="text-xs text-muted-foreground">
        Latest participating vessel metrics in the selected monitoring window.
      </p>
    </CardHeader>
    <CardContent>
      {loading ? (
        <div className="space-y-3">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      ) : !vesselRates.length ? (
        <div className="flex h-[260px] items-center justify-center rounded-md border border-dashed border-muted px-4 text-center text-xs text-muted-foreground">
          No vessel telemetry has been recorded in the selected time window.
        </div>
      ) : (
        <div className="space-y-2">
          {vesselRates.slice(0, 5).map((vessel, index) => (
            <div key={`${vessel.vesselId}-${index}`}>
              <div className="rounded-lg p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-foreground">{vessel.vesselId}</p>
                    <p className="text-xs text-muted-foreground">
                      {vessel.contractId ? `Linked ${vessel.contractId}` : 'Unlinked contract'}
                    </p>
                  </div>
                  <Badge className="bg-slate-100 text-slate-800">
                    {formatNumber(vessel.currentSoc || 0, 0)}% SoC
                  </Badge>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Discharge rate</div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">
                      {formatNumber(vessel.dischargeRateKw || 0, 1)} kW
                    </div>
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Telemetry timestamp</div>
                    <div className="mt-1 text-sm font-semibold text-slate-900">
                      {formatTimestamp(vessel.timestamp)}
                    </div>
                  </div>
                </div>
              </div>
              {index < Math.min(vesselRates.length, 5) - 1 ? <hr /> : null}
            </div>
          ))}
        </div>
      )}
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
  const [selectedCurveId, setSelectedCurveId] = useState('all')

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
  const vesselCurve = snapshot?.vesselCurve || []
  const availableEvents = snapshot?.availableEvents || []
  const selectedSeries = selectedCurveId === 'all'
    ? loadCurve
    : vesselCurve.find((series) => series.vesselId === selectedCurveId)?.points || []
  const selectedCurveMeta = selectedCurveId === 'all'
    ? null
    : vesselCurve.find((series) => series.vesselId === selectedCurveId) || null
  const chartPath = buildPath(selectedSeries, 540, 180)
  const { maxValue: maxCurveValue, minValue: minCurveValue, valueRange } = getCurveBounds(selectedSeries)
  const tickValues = getTickValues(maxCurveValue, minCurveValue)
  const graphSummaryLabel = selectedCurveMeta
    ? `Filtered to ${selectedCurveMeta.vesselId}`
    : `Aggregate across ${vesselRates.length} vessels`
  const latestEnergyValue = selectedSeries.at(-1)?.cumulativeEnergyDischargedKwh
    ?? selectedSeries.at(-1)?.energyDischargedKwh
    ?? 0

  useEffect(() => {
    if (selectedCurveId === 'all') return
    const stillExists = vesselCurve.some((series) => series.vesselId === selectedCurveId)
    if (!stillExists) {
      setSelectedCurveId('all')
    }
  }, [selectedCurveId, vesselCurve])

  if (!canViewDashboard) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <Gauge className="mx-auto mb-4 h-12 w-12 text-slate-400" />
          <h3 className="mb-2 text-lg font-semibold text-gray-900">Access Denied</h3>
          <p className="text-gray-600">Only power operator accounts can access the DR monitoring dashboard.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
        <div className="mb-2">
          <h1 className="text-3xl font-bold text-gray-900">DR Monitoring Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Last updated:{' '}
            <span className="text-sm text-muted-foreground">
              {snapshot?.updatedAt ? new Date(snapshot.updatedAt).toLocaleString() : '—'}
            </span>
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="flex items-center gap-2">
            <Label className="text-sm font-medium text-muted-foreground" htmlFor="eventId">
              Current event
            </Label>
            <select
              id="eventId"
              className={cn(selectClassName, 'sm:min-w-[240px]')}
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
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setIsLoading(true)
              loadDashboard()
            }}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {error ? (
        <Card className="border-destructive bg-destructive/5">
          <CardContent className="pt-4">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader className="flex flex-col gap-3 pb-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-1.5">
            <CardTitle className="text-md font-light">Filters</CardTitle>
            <p className="text-sm text-muted-foreground">
              Dashboard refreshes automatically every 10 seconds.
            </p>
          </div>
          <div className="grid w-full gap-4 md:grid-cols-2 lg:max-w-2xl">
            <div className="space-y-2">
              <Label htmlFor="periodHours">Time Period</Label>
              <select
                id="periodHours"
                className={selectClassName}
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
          </div>
        </CardHeader>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(320px,1fr)]">
        <EventSummaryCard selectedEvent={selectedEvent} summary={summary} loading={isLoading} />
        <EventDetailsCard selectedEvent={selectedEvent} summary={summary} loading={isLoading} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="mb-4 flex items-center gap-2 text-md font-light">
              <LineChart className="h-4 w-4 text-muted-foreground" />
              Energy Discharged Over Time
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              Measurement-backed discharged energy, aggregated by default and filterable by vessel. Baseline grid load is not yet available in the current schema.
            </p>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-72 w-full" />
            ) : (selectedSeries.length || vesselCurve.length) ? (
              <div className="space-y-4">
                <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
                  <div className="grid gap-3 sm:grid-cols-3 xl:flex-1">
                    <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3">
                      <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Scope</div>
                      <div className="mt-1 text-sm font-semibold leading-5 text-slate-900">{graphSummaryLabel}</div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3">
                      <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Peak</div>
                      <div className="mt-1 text-sm font-semibold text-slate-900">{formatNumber(maxCurveValue || 0, 2)} kWh</div>
                    </div>
                    <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3">
                      <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Latest</div>
                      <div className="mt-1 text-sm font-semibold text-slate-900">
                        {selectedCurveMeta
                          ? `${formatNumber(selectedCurveMeta.totalEnergyDischargedKwh || latestEnergyValue, 2)} kWh`
                          : `${formatNumber(latestEnergyValue, 2)} kWh total`}
                      </div>
                    </div>
                  </div>
                  <div className="space-y-2 xl:w-72">
                    <Label htmlFor="curveFilter">Graph Filter</Label>
                    <select
                      id="curveFilter"
                      className={selectClassName}
                      value={selectedCurveId}
                      onChange={(event) => setSelectedCurveId(event.target.value)}
                    >
                      <option value="all">All vessels</option>
                      {vesselCurve.map((series) => (
                        <option key={series.vesselId} value={series.vesselId}>
                          {series.vesselId} · {formatNumber(series.totalEnergyDischargedKwh || 0, 2)} kWh
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="rounded-xl border border-slate-200 bg-[linear-gradient(180deg,_rgba(248,250,252,0.92),_rgba(255,255,255,1))] p-4">
                  <div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-baseline sm:justify-between">
                    <div>
                      <div className="text-sm font-semibold text-slate-900">
                        {selectedCurveMeta ? selectedCurveMeta.vesselId : 'All participating vessels'}
                      </div>
                      <div className="text-xs text-slate-500">
                        {selectedCurveMeta ? `Contract ${selectedCurveMeta.contractId || 'unlinked'}` : 'Aggregate discharged energy'}
                      </div>
                    </div>
                    <div className="text-xs text-slate-500">
                      {selectedSeries[0] ? new Date(selectedSeries[0].timestamp).toLocaleTimeString() : ''}
                      {' '}to{' '}
                      {selectedSeries.at(-1) ? new Date(selectedSeries.at(-1).timestamp).toLocaleTimeString() : ''}
                    </div>
                  </div>
                  <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-3">
                    <div className="flex h-72 flex-col justify-between pb-8 pr-1 text-[11px] font-medium text-slate-500">
                      {tickValues.map((tick) => (
                        <span key={tick}>{formatNumber(tick, 1)} kWh</span>
                      ))}
                    </div>
                    <svg
                      viewBox="0 0 560 220"
                      className="h-72 w-full overflow-visible"
                      role="img"
                      aria-label="Energy discharged over time"
                    >
                      <defs>
                        <linearGradient id="curve-fill" x1="0" x2="0" y1="0" y2="1">
                          <stop offset="0%" stopColor="#0f766e" stopOpacity="0.18" />
                          <stop offset="100%" stopColor="#0f766e" stopOpacity="0.02" />
                        </linearGradient>
                      </defs>
                      {[0, 1, 2].map((gridLine) => {
                        const y = 20 + gridLine * 85
                        return <line key={gridLine} x1="10" y1={y} x2="550" y2={y} stroke="#dbe4ee" strokeDasharray="4 8" strokeWidth="1" />
                      })}
                      <line x1="10" y1="190" x2="550" y2="190" stroke="#94a3b8" strokeWidth="1" />
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
                      {selectedSeries.map((point, index) => {
                        const { x, y } = getPointCoordinates(point, index, selectedSeries, 540, 170, minCurveValue, valueRange)
                        return (
                          <g key={point.timestamp}>
                            <circle cx={10 + x} cy={10 + y} r="4" fill="#0f766e" />
                            <circle cx={10 + x} cy={10 + y} r="7.5" fill="#0f766e" fillOpacity="0.10" />
                          </g>
                        )
                      })}
                      {selectedSeries[0] ? (
                        <text x="10" y="214" fill="#64748b" fontSize="12">
                          {new Date(selectedSeries[0].timestamp).toLocaleTimeString()}
                        </text>
                      ) : null}
                      {selectedSeries.at(-1) ? (
                        <text x="442" y="214" fill="#64748b" fontSize="12">
                          {new Date(selectedSeries.at(-1).timestamp).toLocaleTimeString()}
                        </text>
                      ) : null}
                    </svg>
                  </div>
                </div>
                <p className="text-xs text-slate-500">
                  {snapshot?.baselineAvailable
                    ? 'Baseline grid load data is included.'
                    : 'Baseline grid load is unavailable in the current telemetry model, so this chart shows discharged energy only.'}
                </p>
              </div>
            ) : (
              <div className="rounded-md border border-dashed border-muted px-4 py-10 text-center text-sm text-muted-foreground">
                No telemetry has been recorded in the selected time window.
              </div>
            )}
          </CardContent>
        </Card>

        <VesselTelemetryCard vesselRates={vesselRates} loading={isLoading} />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <DashboardMetricCard
          title="Total Energy Delivered"
          value={`${formatNumber(summary.totalEnergyDeliveredKwh || 0)} kWh`}
          helper={selectedEvent ? `Target ${formatNumber(summary.targetEnergyKwh || 0)} kWh` : 'Select a DR event to monitor'}
          icon={Zap}
          loading={isLoading}
          valueClassName="text-3xl font-medium"
        />
        <DashboardMetricCard
          title="Progress Toward Goal"
          value={`${formatNumber(summary.progressPercent || 0)}%`}
          helper="Computed from event target energy and recorded telemetry"
          icon={Activity}
          loading={isLoading}
          valueClassName="text-3xl font-medium"
        />
        <DashboardMetricCard
          title="Active Vessels"
          value={String(summary.activeVessels || 0)}
          helper="Latest vessel telemetry in the selected time window"
          icon={Ship}
          loading={isLoading}
          valueClassName="text-3xl font-medium"
        />
        <DashboardMetricCard
          title="Monitoring Window"
          value={PERIOD_OPTIONS.find((option) => option.value === filters.periodHours)?.label || 'Last 24 hours'}
          helper={selectedEvent ? formatDateRange(selectedEvent.startTime, selectedEvent.endTime) : 'No event selected'}
          icon={Timer}
          loading={isLoading}
          valueClassName="text-xl font-medium leading-snug"
        />
      </div>
    </div>
  )
}

export default PowerDashboard
