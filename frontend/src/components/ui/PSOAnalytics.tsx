import { CSSProperties, useEffect, useMemo, useRef, useState } from 'react'
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LineElement,
  LinearScale,
  PointElement,
  Title,
  Tooltip,
} from 'chart.js'
import { BarChart3 } from 'lucide-react'
import { Bar, Line } from 'react-chartjs-2'

import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, Filler)

const ENERGY_WINDOW_OPTIONS = [
  { value: '24', label: '24h' },
  { value: '72', label: '72h' },
  { value: '168', label: '7d' },
  { value: '336', label: '14d' },
  { value: 'all', label: 'All' },
]

const STATUS_COLORS: Record<string, string> = {
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

const formatNumber = (value: number | string | undefined, fractionDigits = 1) =>
  new Intl.NumberFormat(undefined, {
    maximumFractionDigits: fractionDigits,
    minimumFractionDigits: fractionDigits,
  }).format(Number(value || 0))

// ─── Energy Trend ────────────────────────────────────────────────────────────

interface TimeSeriesPoint {
  timestamp: string
  energyDischargedKwh: number | string
}

interface EnergyTrendChartProps {
  series: TimeSeriesPoint[]
  grain: string
  isLoading: boolean
}

export function EnergyTrendChart({ series, grain, isLoading }: EnergyTrendChartProps) {
  const [energyWindow, setEnergyWindow] = useState('168')
  const chartRef = useRef<ChartJS>(null)

  const filteredEnergySeries = useMemo(() => {
    if (!series.length || energyWindow === 'all') return series
    const windowHours = Number(energyWindow)
    if (!Number.isFinite(windowHours) || windowHours <= 0) return series
    const latestTimestamp = new Date(series.at(-1)?.timestamp || 0).getTime()
    if (!Number.isFinite(latestTimestamp) || latestTimestamp <= 0) return series
    const cutoff = latestTimestamp - windowHours * 60 * 60 * 1000
    const sliced = series.filter((point) => {
      const timestamp = new Date(point.timestamp).getTime()
      return Number.isFinite(timestamp) && timestamp >= cutoff
    })
    return sliced.length ? sliced : series
  }, [energyWindow, series])

  const energyChartData = useMemo(
    () => ({
      labels: filteredEnergySeries.map((point) => {
        const timestamp = new Date(point.timestamp)
        if (grain === 'hour') {
          return timestamp.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric' })
        }
        return timestamp.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      }),
      datasets: [
        {
          label: 'Energy Discharged (kWh)',
          data: filteredEnergySeries.map((point) => Number(point.energyDischargedKwh || 0)),
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37, 99, 235, 0.05)',
          pointRadius: 0,
          pointHoverRadius: 4,
          borderWidth: 3,
          tension: 0.3,
          fill: true,
        },
      ],
    }),
    [filteredEnergySeries, grain]
  )

  const energyChartOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index' as const,
        intersect: false,
      },
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: {
          title: { display: true, text: 'Energy Discharged (kWh)' },
          beginAtZero: true,
          grid: {
            display: true, // Hide grid lines on y-axis
            lineWidth: 0.5
            },
        },
        x: {
          title: { display: true, text: 'Time' },
          ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 10 },
          grid: {
            display: true, // Hide grid lines on x-axis
            lineWidth: 0.5
            },
        },
      },
    }),
    []
  )

  useEffect(() => {
    const raf = requestAnimationFrame(() => {
      const chart = chartRef.current
      if (!chart) return
      const { ctx, chartArea } = chart
      if (!chartArea) return
      const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
      gradient.addColorStop(0, 'rgba(37, 99, 235, 0.3)')
      gradient.addColorStop(1, 'rgba(37, 99, 235, 0.02)')
      chart.data.datasets[0].backgroundColor = gradient
      chart.update('none')
    })
    return () => cancelAnimationFrame(raf)
  }, [filteredEnergySeries])

  return (
    <Card>
      <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <CardTitle className="text-lg font-light">
            Energy Discharge Over Time
          </CardTitle>
        </div>
        <div className="flex items-center gap-3">
            <Label htmlFor="energy-window" className="whitespace-nowrap">
                Chart Time Window
            </Label>
            <select
                id="energy-window"
                className="h-9 w-fit rounded-md border border-input bg-background px-3 py-1 text-sm"
                value={energyWindow}
                onChange={(e) => setEnergyWindow(e.target.value)}
            >
                {ENERGY_WINDOW_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                    {option.label}
                </option>
                ))}
            </select>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-96 w-full" />
        ) : filteredEnergySeries.length ? (
          <div className="h-96 w-full">
            <Line ref={chartRef as React.RefObject<ChartJS<'line', number[], string>>} data={energyChartData} options={energyChartOptions} />
          </div>
        ) : (
          <div className="rounded-lg border border-dashed p-6 text-sm text-slate-600">
            No measurements are available for this filter combination.
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Status Mix ───────────────────────────────────────────────────────────────

interface StatusEntry {
  status: string
  count: number
  percent: number | string
}

interface StatusMixProps {
  statusDistribution: StatusEntry[]
  isLoading: boolean
}

export function StatusMix({ statusDistribution, isLoading }: StatusMixProps) {
  const topStatuses = statusDistribution.slice(0, 4)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Status Mix</CardTitle>
        <CardDescription>Distribution of event lifecycle states in the filtered result set.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading ? (
          <Skeleton className="h-48 w-full" />
        ) : topStatuses.length ? (
          topStatuses.map((entry) => (
            <div key={entry.status} className="rounded-lg border border-slate-200 p-3">
              <div className="mb-2 flex items-center justify-between">
                <Badge className={STATUS_COLORS[entry.status] || STATUS_COLORS.Created}>{entry.status}</Badge>
                <span className="text-sm font-semibold text-slate-900">{entry.count}</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-100">
                <div
                  className="h-2 rounded-full bg-slate-600"
                  style={{ width: `${Math.max(4, Number(entry.percent || 0))}%` }}
                />
              </div>
            </div>
          ))
        ) : (
          <div className="rounded-lg border border-dashed p-6 text-sm text-slate-600">
            No status distribution available.
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Dispatch Heatmap ─────────────────────────────────────────────────────────

interface HeatmapBand {
  label: string
  averagePowerKw: number | string
}

interface HeatmapRow {
  dayLabel: string
  bands: HeatmapBand[]
}

interface DispatchHeatmapProps {
  heatmap: HeatmapRow[]
  isLoading: boolean
}

const formatCurrency = (value: number | null | undefined) =>
  value == null ? '—' : `$${Number(value).toFixed(2)}`

export function DispatchHeatmap({ heatmap, isLoading }: DispatchHeatmapProps) {
  const allValues = useMemo(
    () => heatmap.flatMap((row) => row.bands.map((b) => Number(b.averagePowerKw || 0))),
    [heatmap]
  )
  const minPower = useMemo(() => (allValues.length ? Math.min(...allValues) : 0), [allValues])
  const maxPower = useMemo(() => (allValues.length ? Math.max(...allValues) : 0), [allValues])

  const cellStyle = (value: number | string): CSSProperties => {
    const v = Number(value || 0)
    const range = maxPower - minPower
    const ratio = range > 0 ? Math.min((v - minPower) / range, 1) : 0
    const opacity = 0.06 + ratio * 0.79
    return {
      backgroundColor: `rgba(37, 99, 235, ${opacity.toFixed(2)})`,
      color: ratio > 0.5 ? '#ffffff' : '#1e293b',
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Dispatch Heatmap</CardTitle>
        <CardDescription>Average dispatched power by day-of-week and hour of day.</CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : heatmap.length ? (
          <>
            <div className="grid grid-cols-[min-content_repeat(5,1fr)] gap-2 text-xs">
              <div className="font-semibold text-slate-500">Day</div>
              <div className="font-semibold text-slate-500">00-04</div>
              <div className="font-semibold text-slate-500">04-08</div>
              <div className="font-semibold text-slate-500">08-12</div>
              <div className="font-semibold text-slate-500">12-18</div>
              <div className="font-semibold text-slate-500">18-24</div>
              {heatmap.map((row) => (
                <div key={row.dayLabel} className="contents">
                  <div className="rounded border border-slate-200 p-2 font-semibold text-slate-700">{row.dayLabel}</div>
                  {row.bands.map((band) => (
                    <div
                      key={`${row.dayLabel}-${band.label}`}
                      className="rounded border border-slate-200 p-2 text-center font-medium"
                      style={cellStyle(band.averagePowerKw)}
                      title={`${band.label}: ${formatNumber(band.averagePowerKw, 1)} kW`}
                    >
                      {formatNumber(band.averagePowerKw, 1)}
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
              <span>{formatNumber(minPower, 1)} kW</span>
              <div
                className="h-2 flex-1 rounded"
                style={{ background: 'linear-gradient(to right, rgba(37,99,235,0.06), rgba(37,99,235,0.85))' }}
              />
              <span>{formatNumber(maxPower, 1)} kW</span>
            </div>
          </>
        ) : (
          <div className="rounded-lg border border-dashed p-6 text-sm text-slate-600">
            Heatmap data will appear once measurement telemetry is present.
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Financial Trend ──────────────────────────────────────────────────────────

interface FinancialTimeSeriesPoint {
  timestamp: string
  payoutUsd: number | string
}

interface FinancialTrendChartProps {
  series: FinancialTimeSeriesPoint[]
  grain: string
  isLoading: boolean
}

export function FinancialTrendChart({ series, grain, isLoading }: FinancialTrendChartProps) {
  const chartRef = useRef<ChartJS>(null)

  const chartData = useMemo(
    () => ({
      labels: series.map((point) => {
        const ts = new Date(point.timestamp)
        if (grain === 'hour') {
          return ts.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric' })
        }
        return ts.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      }),
      datasets: [
        {
          label: 'Payout (USD)',
          data: series.map((point) => Number(point.payoutUsd || 0)),
          borderColor: 'rgb(29, 157, 150)',
          backgroundColor: 'rgba(29, 157, 150, 0.05)',
          pointRadius: 0,
          pointHoverRadius: 4,
          borderWidth: 3,
          tension: 0.3,
          fill: true,
        },
      ],
    }),
    [series, grain]
  )

  const chartOptions = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index' as const, intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx: { parsed: { y: number } }) => ` ${formatCurrency(ctx.parsed.y)}`,
          },
        },
      },
      scales: {
        y: {
          title: { display: true, text: 'Payout (USD)' },
          beginAtZero: true,
          grid: { display: true, lineWidth: 0.5 },
          ticks: {
            callback: (value: number | string) => `$${Number(value).toFixed(0)}`,
          },
        },
        x: {
          title: { display: true, text: 'Time' },
          ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 10 },
          grid: { display: true, lineWidth: 0.5 },
        },
      },
    }),
    []
  )

  useEffect(() => {
    const raf = requestAnimationFrame(() => {
      const chart = chartRef.current
      if (!chart) return
      const { ctx, chartArea } = chart
      if (!chartArea) return
      const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
      gradient.addColorStop(0, 'rgba(29, 157, 150, 0.3)')
      gradient.addColorStop(1, 'rgba(29, 157, 150, 0.02)')
      chart.data.datasets[0].backgroundColor = gradient
      chart.update('none')
    })
    return () => cancelAnimationFrame(raf)
  }, [series])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-light">Financial Payout Over Time</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : series.length ? (
          <div className="h-64 w-full">
            <Line ref={chartRef as React.RefObject<ChartJS<'line', number[], string>>} data={chartData} options={chartOptions} />
          </div>
        ) : (
          <div className="rounded-lg border border-dashed p-6 text-sm text-slate-600">
            No settled contracts in the selected period.
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Event Value Chart ────────────────────────────────────────────────────────

interface EventBreakdownEntry {
  eventId: string
  startTime: string
  targetValueUsd: number | string
  actualPayoutUsd: number | string
  deliveryRatePct: number | string
}

interface EventValueChartProps {
  eventBreakdown: EventBreakdownEntry[]
  isLoading: boolean
}

export function EventValueChart({ eventBreakdown, isLoading }: EventValueChartProps) {
  const chartRef = useRef<ChartJS>(null)
  const visible = useMemo(() => eventBreakdown.slice(0, 8), [eventBreakdown])

  const chartData = useMemo(
    () => ({
      labels: visible.map((entry) => {
        const ts = new Date(entry.startTime)
        return ts.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
      }),
      datasets: [
        {
          label: 'Actual Payout',
          data: visible.map((entry) => Number(entry.actualPayoutUsd || 0)),
          backgroundColor: 'rgba(29, 157, 150, 0.7)',
          borderRadius: 4,
        },
        {
          label: 'Target Value',
          data: visible.map((entry) =>
            Math.max(0, Number(entry.targetValueUsd || 0) - Number(entry.actualPayoutUsd || 0))
          ),
          backgroundColor: 'rgba(203, 213, 225, 0.5)',
          borderRadius: 4,
        },
      ],
    }),
    [visible]
  )

  const chartOptions = useMemo(
    () => ({
      animation: false as const,
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y' as const,
      interaction: { mode: 'index' as const, intersect: false },
      plugins: {
        legend: { display: true, position: 'bottom' as const },
        tooltip: {
          callbacks: {
            label: (ctx: { dataset: { label: string }; parsed: { x: number } }) =>
              ` ${ctx.dataset.label}: ${formatCurrency(ctx.parsed.x)}`,
          },
        },
      },
      scales: {
        x: {
          stacked: true,
          title: { display: true, text: 'Value (USD)' },
          grid: { display: true, lineWidth: 0.5 },
          ticks: {
            callback: (value: number | string) => `$${Number(value).toFixed(0)}`,
          },
        },
        y: { stacked: true, grid: { display: false } },
      },
    }),
    []
  )

  useEffect(() => {
    const raf = requestAnimationFrame(() => {
      const chart = chartRef.current
      if (!chart) return
      const { ctx, chartArea } = chart
      if (!chartArea) return
      const gradient = ctx.createLinearGradient(chartArea.left, 0, chartArea.right, 0)
      gradient.addColorStop(0, 'rgba(29, 157, 150, 0.3)')
      gradient.addColorStop(1, 'rgba(29, 157, 150, 0.85)')
      chart.data.datasets[0].backgroundColor = gradient
      chart.update('none')
    })
    return () => cancelAnimationFrame(raf)
  }, [visible])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Target vs. Actual Payout per Event</CardTitle>
        <CardDescription>
          How much of each event's theoretical value was actually settled. Gap = undelivered value.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-64 w-full" />
        ) : visible.length ? (
          <div className="h-64 w-full">
            <Bar ref={chartRef as React.RefObject<ChartJS<'bar', number[], string>>} data={chartData} options={chartOptions} />
          </div>
        ) : (
          <div className="rounded-lg border border-dashed p-6 text-sm text-slate-600">
            No events to display for the selected filters.
          </div>
        )}
      </CardContent>
    </Card>
  )
}
