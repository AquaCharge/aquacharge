import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { FileCheck, LineChart, Zap, Wallet } from 'lucide-react'
import { Link } from 'react-router-dom'

const SOC_TICKS = [100, 50, 0]

const buildSocPath = (points, width, height) => {
  if (!points?.length) return ''
  const values = points.map((point) => Number(point.socPercent ?? 0))
  const maxValue = Math.max(...values, 1)
  return points
    .map((point, index) => {
      const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width
      const y = height - (Number(point.socPercent ?? 0) / maxValue) * height
      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`
    })
    .join(' ')
}

export const MetricCard = ({ title, value, helper, loading }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
      <CardTitle className="text-md font-light">{title}</CardTitle>
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

export const StateOfChargeCard = ({ percent, loading }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
      <CardTitle className="text-md font-light">State of charge</CardTitle>
    </CardHeader>
    <CardContent>
      {loading ? (
        <Skeleton className="h-3 w-full rounded-full" />
      ) : (
        <>
          <div className="flex items-center justify-end text-sm mb-2">
            <span className="font-medium">
              {percent != null ? `${percent}%` : '—'}
            </span>
          </div>
          <div className="h-3 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-blue-500/60 to-blue-600 transition-all duration-500 ease-out"
              style={{ width: percent != null ? `${Math.min(100, Math.max(0, percent))}%` : '0%' }}
            />
          </div>
        </>
      )}
    </CardContent>
  </Card>
)

/** All-time stats: contracts completed, total kWh discharged, total earnings */
export const AllTimeCard = ({ metrics, loading }) => {
  const contractsCompleted = metrics?.contractsCompleted ?? 0
  const totalKwh = metrics?.totalKwhDischarged ?? 0
  const totalEarnings = metrics?.totalEarnings ?? 0

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
        <CardTitle className="text-md font-light">All Time</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <>
            <Skeleton className="h-6 w-20 mb-2" />
            <Skeleton className="h-6 w-24 mb-2" />
            <Skeleton className="h-6 w-20" />
          </>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <FileCheck className="h-4 w-4 text-muted-foreground shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Contracts completed</p>
                <p className="text-lg font-semibold tabular-nums">{contractsCompleted}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-muted-foreground shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Total kW discharged</p>
                <p className="text-lg font-semibold tabular-nums">
                  {typeof totalKwh === 'number' ? totalKwh.toFixed(1) : totalKwh} kWh
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Wallet className="h-4 w-4 text-muted-foreground shrink-0" />
              <div>
                <p className="text-xs text-muted-foreground">Total earnings</p>
                <p className="text-lg font-semibold tabular-nums">
                  ${typeof totalEarnings === 'number' ? totalEarnings.toFixed(2) : totalEarnings}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export const WeeklyEarningsCard = ({ weeklyEarnings, loading }) => {
  const rawDaily = weeklyEarnings?.dailyEarnings ?? []
  const total = weeklyEarnings?.total ?? 0

  // Normalize to the last 7 days of earnings, padding on the left with zeros if needed.
  const daily = (() => {
    const source = Array.isArray(rawDaily) ? rawDaily : []
    const lastSeven = source.slice(-7)
    const padded = [...lastSeven]
    while (padded.length < 7) padded.unshift(0)
    return padded
  })()

  // Find global max so tallest bar gets the full opacity
  const maxEarnings = Math.max(1, ...daily)
  const minOpacity = 0.18 // for the bottom of the bar (use a subtle glow)
  const maxOpacity = 0.85 // for the very top of the tallest bar

  // Build dynamic day labels for the past 7 days, oldest on the left, today on the right.
  const today = new Date()
  const dayLabels = Array.from({ length: 7 }, (_, index) => {
    const d = new Date(today)
    // Index 6 is today, 5 is yesterday, ..., 0 is 6 days ago.
    d.setDate(d.getDate() - (6 - index))
    return d.toLocaleDateString(undefined, { weekday: 'short' })
  })

  const todayIndex = 6

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
        <CardTitle className="text-md font-light">Earnings</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <>
            <Skeleton className="h-8 w-24 mb-4" />
            <Skeleton className="h-40 w-full" />
          </>
        ) : (
          <>
            <div className="text-3xl mb-1">
              ${Number(total).toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground mb-4">Last 7 days</p>
            <div className="flex flex-col h-40">
              {/* Bar chart area: bars all bottom-aligned and day labels on a row below */}
              <div className="flex items-end gap-1 flex-1 min-h-0">
                {daily.map((earnings, i) => {
                  const isToday = i === todayIndex
                  const canvasHeightPx = 120 // room for value/labels
                  const minBarHeightPx = 2

                  let barHeightPx = 0
                  if (maxEarnings > 0 && earnings > 0) {
                    barHeightPx = Math.max(
                      minBarHeightPx,
                      (earnings / maxEarnings) * canvasHeightPx
                    )
                  }

                  // Opacity depends on value. If tallest, use maxOpacity.
                  // Otherwise: linear between minOpacity and maxOpacity.
                  let opacityTop = minOpacity
                  if (maxEarnings > 0 && earnings > 0) {
                    // 0 for 0 earnings, maxOpacity for maxEarnings
                    opacityTop =
                      minOpacity +
                      ((Math.min(earnings, maxEarnings) / maxEarnings) * (maxOpacity - minOpacity))
                  }

                  // Use a linear-gradient background: 
                  // - top: accent color, variable opacity
                  // - bottom: accent color, min opacity
                  // #1D9D96 is used for today, otherwise rgba(29,157,150,...)
                  const baseColor = isToday ? '29,157,150' : '29,157,150'
                  const style = {
                    height: barHeightPx,
                    background: `linear-gradient(
                      to top,
                      rgba(${baseColor}, ${minOpacity}) 0%,
                      rgba(${baseColor}, ${opacityTop}) 100%
                    )`,
                    borderTopLeftRadius: 6,
                    borderTopRightRadius: 6,
                    transition: "height 0.25s, background 0.25s",
                    marginBottom: 0,
                    // Optionally highlight today with a border
                    ...(isToday ? { boxShadow: "0 0 0 2px #1d9d9680" } : {})
                  }

                  return (
                    <div key={i} className="flex-1 flex flex-col items-center min-w-0 h-full justify-end">
                      {/* Bar value */}
                      <span
                        className="text-xs font-medium text-muted-foreground tabular-nums shrink-0 w-full text-center"
                        style={{ marginBottom: 4, minHeight: 16 }}
                      >
                        {Number(earnings).toFixed(0)}
                      </span>
                      <div
                        className="w-full rounded-t transition-all shrink-0"
                        style={style}
                      />
                    </div>
                  )
                })}
              </div>
              {/* Day labels aligned under all bars */}
              <div className="flex gap-1 mt-1">
                {dayLabels.map((label, i) => {
                  const isToday = i === todayIndex
                  return (
                    <div key={label} className="flex-1 flex flex-col items-center min-w-0">
                      <span
                        className={`text-xs shrink-0 ${
                          isToday ? 'font-semibold text-foreground' : 'text-muted-foreground'
                        }`}
                        style={{ minHeight: 16 }}
                      >
                        {label}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

export const WeeklySocCard = ({ socSeries, socLoading, socError }) => {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-md font-light mb-4">
          State of Charge
        </CardTitle>
        <div className="text-3xl mb-1">
          {(() => {
            try {
              if (
                Array.isArray(socSeries) &&
                socSeries.length > 0 &&
                socSeries[socSeries.length - 1] &&
                typeof socSeries[socSeries.length - 1].socPercent !== "undefined" &&
                socSeries[socSeries.length - 1].socPercent !== null &&
                !isNaN(Number(socSeries[socSeries.length - 1].socPercent))
              ) {
                return `${Number(socSeries[socSeries.length - 1].socPercent).toFixed(1)}%`;
              } else if (Array.isArray(socSeries) && socSeries.length > 0) {
                return "0.0%";
              } else {
                return "—";
              }
            } catch (err) {
              return "—";
            }
          })()}
        </div>
        <p className="text-xs text-muted-foreground mb-4">Current SoC</p>
      </CardHeader>
      <CardContent>
        {socLoading ? (
          <Skeleton className="h-40 w-full" />
        ) : socError ? (
          <div className="h-40 rounded-md border border-destructive/40 bg-destructive/5 flex items-center justify-center px-4 text-xs text-destructive text-center">
            {socError}
          </div>
        ) : !socSeries?.length ? (
          <div className="h-40 rounded-md border border-dashed border-muted flex items-center justify-center px-4 text-xs text-muted-foreground text-center">
            No SoC telemetry has been recorded for this vessel in the past 7 days.
          </div>
        ) : (
          <div className="space-y-3">
           
            <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-2">
              <div className="flex h-40 flex-col justify-between pr-2 text-[10px] font-medium text-muted-foreground">
                {SOC_TICKS.map((tick) => (
                  <span key={tick}>{tick}%</span>
                ))}
              </div>
              <svg
                viewBox="0 0 560 200"
                className="h-40 w-full overflow-visible"
                role="img"
                aria-label="Weekly state of charge"
              >
                <defs>
                  <linearGradient id="soc-curve-fill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#2563eb" stopOpacity="0.2" />
                    <stop offset="100%" stopColor="#2563eb" stopOpacity="0.02" />
                  </linearGradient>
                </defs>
                {[0, 1, 2].map((lineIndex) => {
                  const y = 20 + lineIndex * 70
                  return (
                    <line
                      key={lineIndex}
                      x1="10"
                      y1={y}
                      x2="550"
                      y2={y}
                      stroke="#e5e7eb"
                      strokeDasharray="4 6"
                      strokeWidth="1"
                    />
                  )
                })}
                <line x1="10" y1="180" x2="550" y2="180" stroke="#9ca3af" strokeWidth="1" />
                <line x1="10" y1="20" x2="10" y2="180" stroke="#d1d5db" strokeWidth="1" />
                {(() => {
                  const path = buildSocPath(socSeries, 540, 160)
                  if (!path) return null
                  return (
                    <>
                      <path
                        d={`${path} L 540 160 L 0 160 Z`}
                        transform="translate(10,20)"
                        fill="url(#soc-curve-fill)"
                      />
                      <path
                        d={path}
                        transform="translate(10,20)"
                        fill="none"
                        stroke="#2563eb"
                        strokeWidth="2.5"
                        strokeLinejoin="round"
                        strokeLinecap="round"
                      />
                      {socSeries.map((point, index) => {
                        const values = socSeries.map((p) => Number(p.socPercent ?? 0))
                        const maxValue = Math.max(...values, 1)
                        const x =
                          socSeries.length === 1
                            ? 540 / 2
                            : (index / (socSeries.length - 1)) * 540
                        const y = 160 - (Number(point.socPercent ?? 0) / maxValue) * 160
                        return (
                          <g key={point.timestamp}>
                            <circle cx={10 + x} cy={20 + y} r="3.5" fill="#2563eb" />
                            <circle cx={10 + x} cy={20 + y} r="6.5" fill="#2563eb" fillOpacity="0.14" />
                          </g>
                        )
                      })}
                    </>
                  )
                })()}
                <text x="10" y="196" fill="#6b7280" fontSize="11">
                  {new Date(socSeries[0].timestamp).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                  })}
                </text>
                <text x="472" y="196" fill="#6b7280" fontSize="11">
                  {new Date(socSeries[socSeries.length - 1].timestamp).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                  })}
                </text>
              </svg>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export const QuickActionsCard = ({ title, description, items }) => {
  return (
    <Card className="">
      <CardHeader>
        <CardTitle className="text-md font-light">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-1">
          {items?.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="group block w-full p-4 text-left border rounded-lg hover:bg-blue-200 transition-colors bg-blue-50 border-blue-200"
            >
              <div className="flex items-center space-x-3 justify-between">
                <div className="flex items-center space-x-3">
                  {item.icon}
                  <div>
                    <p className="font-light">{item.label}</p>
                  </div>
                </div>
                <span className="text-lg text-blue-200 ml-3 group-hover:text-blue-700">{'>'}</span>
              </div>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
