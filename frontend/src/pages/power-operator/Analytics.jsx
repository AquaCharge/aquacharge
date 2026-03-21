import { useEffect, useMemo, useState } from 'react'
import { Activity, AlertCircle, DollarSign, Gauge, RefreshCw, Timer, TrendingUp, Users, Zap, Settings2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { DispatchHeatmap, EnergyTrendChart, EventValueChart, FinancialTrendChart, StatusMix } from '@/components/ui/PSOAnalytics'
import { getApiEndpoint } from '@/config/api'
import { useAuth } from '@/contexts/AuthContext'
import { getMockPSOAnalyticsSnapshot } from './MockPSOData'

const PERIOD_OPTIONS = [
  { value: '24', label: 'Last 24 hours' },
  { value: '72', label: 'Last 72 hours' },
  { value: '168', label: 'Last 7 days' },
  { value: '336', label: 'Last 14 days' },
  { value: '720', label: 'Last 30 days' },
]

const GRAIN_OPTIONS = [
  { value: 'hour', label: 'Hourly' },
  { value: 'day', label: 'Daily' },
]

const formatNumber = (value, fractionDigits = 1) =>
  new Intl.NumberFormat(undefined, {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  }).format(Number(value || 0))

const formatPercent = (value) => `${formatNumber(value || 0, 1)}%`

const formatCurrency = (value) =>
  value == null ? '—' : `$${Number(value).toFixed(2)}`

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

const Analytics = () => {
  const { user } = useAuth()
  const mockAnalyticsEnabled =
    String(import.meta.env.VITE_PSO_ANALYTICS_ENABLE_MOCK || '').toLowerCase() === 'true'
  const [filters, setFilters] = useState({
    eventId: '',
    periodHours: '168',
    grain: 'day',
  })
  const [useMockData, setUseMockData] = useState(false)
  const [snapshot, setSnapshot] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const authToken = localStorage.getItem('auth-token')
  const canViewAnalytics = user?.type_name === 'POWER_OPERATOR'

  const queryString = useMemo(() => {
    const params = new URLSearchParams()
    if (filters.eventId) params.set('eventId', filters.eventId)
    params.set('periodHours', filters.periodHours)
    params.set('grain', filters.grain)
    return params.toString()
  }, [filters])

  const loadAnalytics = async () => {
    if (mockAnalyticsEnabled && useMockData) {
      setError('')
      setSnapshot(getMockPSOAnalyticsSnapshot(filters))
      setIsLoading(false)
      return
    }

    if (!authToken) {
      setError('Missing authentication token.')
      setIsLoading(false)
      return
    }

    setError('')
    try {
      const response = await fetch(getApiEndpoint(`/api/drevents/analytics?${queryString}`), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || payload.details || 'Failed to load analytics')
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
      setError(loadError.message || 'Failed to load analytics.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!canViewAnalytics) {
      setIsLoading(false)
      return
    }
    setIsLoading(true)
    loadAnalytics()
  }, [canViewAnalytics, queryString, useMockData])

  const summary = snapshot?.summary || {}
  const financials = snapshot?.financials || {}
  const availableEvents = snapshot?.availableEvents || []
  const series = snapshot?.timeSeries || []
  const statusDistribution = snapshot?.statusDistribution || []
  const heatmap = snapshot?.heatmap || []
  const financialSeries = financials?.timeSeries || []
  const eventBreakdown = financials?.eventBreakdown || []

  if (!canViewAnalytics) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <Gauge className="mx-auto mb-4 h-12 w-12 text-slate-400" />
          <h3 className="mb-2 text-lg font-semibold text-gray-900">Access Denied</h3>
          <p className="text-gray-600">Only power operator accounts can access analytics.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Historical Analytics</h1>
          <p className="mt-2 text-gray-600">
            Event-level and fleet-level trends for dispatch outcomes, participation, and historical performance.
          </p>
        </div>
        {mockAnalyticsEnabled ? (
          <div className="flex gap-2">
            <Button
              type="button"
              variant={useMockData ? 'default' : 'outline'}
              onClick={() => {
                setIsLoading(true)
                setUseMockData((current) => !current)
              }}
            >
              {useMockData ? 'Using sample data' : 'Use sample data'}
            </Button>
          </div>
        ) : null}
      </div>

      <Card>
        <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings2 className="h-5 w-5" />
          Filters
        </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor="analytics-eventId">DR Event</Label>
            <select
              id="analytics-eventId"
              className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
              value={filters.eventId}
              onChange={(event) => setFilters((current) => ({ ...current, eventId: event.target.value }))}
            >
              <option value="">All matching events</option>
              {availableEvents.map((event) => (
                <option key={event.id} value={event.id}>
                  {event.id} · {event.status} · {event.regionLabel || event.stationId}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="analytics-periodHours">Time Period</Label>
            <select
              id="analytics-periodHours"
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
            <Label htmlFor="analytics-grain">Aggregation</Label>
            <select
              id="analytics-grain"
              className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm"
              value={filters.grain}
              onChange={(event) => setFilters((current) => ({ ...current, grain: event.target.value }))}
            >
              {GRAIN_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-5">
        <MetricCard
          title="Total Energy"
          value={`${formatNumber(summary.totalEnergyDischargedKwh || 0, 1)} kWh`}
          helper="Energy discharged in selected history window"
          icon={Zap}
          loading={isLoading}
        />
        <MetricCard
          title="Average Power"
          value={`${formatNumber(summary.averagePowerKw || 0, 1)} kW`}
          helper="Average V2G contribution across buckets"
          icon={Activity}
          loading={isLoading}
        />
        <MetricCard
          title="Peak Power"
          value={`${formatNumber(summary.peakPowerKw || 0, 1)} kW`}
          helper="Highest aggregated dispatch power"
          icon={Gauge}
          loading={isLoading}
        />
        <MetricCard
          title="Completion Ratio"
          value={formatPercent(summary.completionRatePercent || 0)}
          helper="Completed contracts over finalized contracts"
          icon={Timer}
          loading={isLoading}
        />
        <MetricCard
          title="Participation Rate"
          value={formatPercent(summary.participationRatePercent || 0)}
          helper="Distinct active vessels against capacity"
          icon={Users}
          loading={isLoading}
        />
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <MetricCard
          title="Total Payout"
          value={financials.totalPayoutUsd != null ? formatCurrency(financials.totalPayoutUsd) : '—'}
          helper="Settled contract payments in the selected period"
          icon={DollarSign}
          loading={isLoading}
        />
        <MetricCard
          title="Cost per kWh"
          value={financials.costPerKwhUsd != null ? `${formatCurrency(financials.costPerKwhUsd)}/kWh` : '—'}
          helper="Payout divided by total energy delivered"
          icon={TrendingUp}
          loading={isLoading}
        />
        <MetricCard
          title="Committed Exposure"
          value={financials.committedExposureUsd != null ? formatCurrency(financials.committedExposureUsd) : '—'}
          helper="Value of active and pending contracts not yet settled"
          icon={AlertCircle}
          loading={isLoading}
        />
      </div>

      <EnergyTrendChart series={series} grain={filters.grain} isLoading={isLoading} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(0,2fr)]">
        <StatusMix statusDistribution={statusDistribution} isLoading={isLoading} />
        <DispatchHeatmap heatmap={heatmap} isLoading={isLoading} />
      </div>

      <FinancialTrendChart series={financialSeries} grain={filters.grain} isLoading={isLoading} />

      <EventValueChart eventBreakdown={eventBreakdown} isLoading={isLoading} />
    </div>
  )
}

export default Analytics
