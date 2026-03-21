import { useEffect, useState } from 'react'
import {
  Activity,
  Gauge,
  RefreshCw,
  Ship,
  Timer,
  Zap,
} from 'lucide-react'

import { MetricCard as DashboardMetricCard } from '@/components/ui/DashboardCards'
import { WeeklyPayoutsCard } from '@/components/ui/PSODashboard'
import { EnergyTrendChart } from '@/components/ui/PSOAnalytics'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { getApiEndpoint } from '@/config/api'
import { useAuth } from '@/contexts/AuthContext'
import { getMockPSOAnalyticsSnapshot, getMockPSOWeeklyPayouts } from './MockPSOData'

const USE_MOCK_PSO_DASHBOARD = import.meta.env.VITE_PSO_DASHBOARD_USE_MOCK !== 'false'

const POLL_INTERVAL_MS = 10_000

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

const formatDateRange = (start, end) => {
  if (!start || !end) return 'No dispatch window'
  return `${formatTimestamp(start)} to ${formatTimestamp(end)}`
}

const clampPercent = (value) => Math.max(0, Math.min(100, Number(value || 0)))


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
        <CardTitle className="mb-4 flex items-center gap-2 text-lg font-light">
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
      <CardTitle className="text-lg font-light">
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

const PowerDashboard = () => {
  const { user } = useAuth()
  const [snapshot, setSnapshot] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [weeklyPayouts, setWeeklyPayouts] = useState(null)
  const [payoutsLoading, setPayoutsLoading] = useState(true)
  const [energySeries, setEnergySeries] = useState([])
  const [energyLoading, setEnergyLoading] = useState(true)
  const energyGrain = 'day'

  const authToken = localStorage.getItem('auth-token')
  const canViewDashboard = user?.type_name === 'POWER_OPERATOR'

  const loadDashboard = async () => {
    if (!authToken) {
      setError('Missing authentication token.')
      setIsLoading(false)
      return
    }

    setError('')
    try {
      const response = await fetch(getApiEndpoint('/api/drevents/monitoring?periodHours=24'), {
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
    } catch (loadError) {
      setError(loadError.message || 'Failed to load monitoring dashboard.')
    } finally {
      setIsLoading(false)
    }
  }

  const loadWeeklyPayouts = async () => {
    if (USE_MOCK_PSO_DASHBOARD) {
      setWeeklyPayouts(getMockPSOWeeklyPayouts())
      setPayoutsLoading(false)
      return
    }

    if (!authToken) {
      setPayoutsLoading(false)
      return
    }

    try {
      const response = await fetch(
        getApiEndpoint('/api/drevents/analytics?periodHours=168&grain=day'),
        { headers: { Authorization: `Bearer ${authToken}` } }
      )
      if (!response.ok) throw new Error('Failed to load payout data')
      const payload = await response.json()

      // Convert financials.timeSeries [{timestamp, payoutUsd}] into a 7-element Mon-Sun array
      const daily = [0, 0, 0, 0, 0, 0, 0]
      const now = new Date()
      const weekStartMs = now.getTime() - 6 * 24 * 60 * 60 * 1000
      for (const point of payload?.financials?.timeSeries || []) {
        const ms = new Date(point.timestamp).getTime()
        if (ms < weekStartMs || ms > now.getTime()) continue
        const jsDay = new Date(point.timestamp).getUTCDay() // 0=Sun
        const index = jsDay === 0 ? 6 : jsDay - 1 // Mon=0 … Sun=6
        daily[index] = Number((daily[index] + Number(point.payoutUsd || 0)).toFixed(2))
      }

      setWeeklyPayouts({
        total: Number(daily.reduce((sum, v) => sum + v, 0).toFixed(2)),
        dailyPayouts: daily,
      })
    } catch {
      setWeeklyPayouts(null)
    } finally {
      setPayoutsLoading(false)
    }
  }

  const loadEnergySeries = async () => {
    if (USE_MOCK_PSO_DASHBOARD) {
      // Use 30-day window so the chart's internal window selector (24h/72h/7d/14d/all) has data to work with
      setEnergySeries(getMockPSOAnalyticsSnapshot({ periodHours: '720', grain: energyGrain }).timeSeries)
      setEnergyLoading(false)
      return
    }

    if (!authToken) {
      setEnergyLoading(false)
      return
    }

    try {
      const response = await fetch(
        getApiEndpoint(`/api/drevents/analytics?periodHours=720&grain=${energyGrain}`),
        { headers: { Authorization: `Bearer ${authToken}` } }
      )
      if (!response.ok) throw new Error('Failed to load energy series')
      const payload = await response.json()
      setEnergySeries(payload?.timeSeries || [])
    } catch {
      setEnergySeries([])
    } finally {
      setEnergyLoading(false)
    }
  }

  useEffect(() => {
    if (!canViewDashboard) {
      setIsLoading(false)
      return
    }

    setIsLoading(snapshot === null)
    loadDashboard()
    const timer = window.setInterval(loadDashboard, POLL_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [canViewDashboard])

  useEffect(() => {
    if (!canViewDashboard) return
    loadWeeklyPayouts()
    loadEnergySeries()
  }, [canViewDashboard])

  const selectedEvent = snapshot?.selectedEvent
  const summary = snapshot?.summary || {}

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

      <div className="grid gap-4 xl:grid-cols-[minmax(0,3fr)_minmax(320px,1fr)]">
        <EventSummaryCard selectedEvent={selectedEvent} summary={summary} loading={isLoading} />
        <EventDetailsCard selectedEvent={selectedEvent} summary={summary} loading={isLoading} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <EnergyTrendChart series={energySeries} grain={energyGrain} isLoading={energyLoading} />
        <WeeklyPayoutsCard weeklyPayouts={weeklyPayouts} loading={payoutsLoading} />
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
          value="Last 24 hours"
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
