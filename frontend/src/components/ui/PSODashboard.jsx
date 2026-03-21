import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export const WeeklyPayoutsCard = ({ weeklyPayouts, loading }) => {
  const rawDaily = weeklyPayouts?.dailyPayouts ?? []
  const total = weeklyPayouts?.total ?? 0

  // Normalize to the last 7 days of payouts, padding on the left with zeros if needed.
  const daily = (() => {
    const source = Array.isArray(rawDaily) ? rawDaily : []
    const lastSeven = source.slice(-7)
    const padded = [...lastSeven]
    while (padded.length < 7) padded.unshift(0)
    return padded
  })()

  // Find global max so tallest bar gets the full opacity
  const maxPayout = Math.max(1, ...daily)
  const minOpacity = 0.18
  const maxOpacity = 0.85

  // Build dynamic day labels for the past 7 days, oldest on the left, today on the right.
  const today = new Date()
  const dayLabels = Array.from({ length: 7 }, (_, index) => {
    const d = new Date(today)
    d.setDate(d.getDate() - (6 - index))
    return d.toLocaleDateString(undefined, { weekday: 'short' })
  })

  const todayIndex = 6

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
        <CardTitle className="text-lg font-light">Payouts</CardTitle>
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
              <div className="flex items-end gap-1 flex-1 min-h-0">
                {daily.map((payout, i) => {
                  const isToday = i === todayIndex
                  const canvasHeightPx = 120
                  const minBarHeightPx = 2

                  let barHeightPx = 0
                  if (maxPayout > 0 && payout > 0) {
                    barHeightPx = Math.max(
                      minBarHeightPx,
                      (payout / maxPayout) * canvasHeightPx
                    )
                  }

                  let opacityTop = minOpacity
                  if (maxPayout > 0 && payout > 0) {
                    opacityTop =
                      minOpacity +
                      ((Math.min(payout, maxPayout) / maxPayout) * (maxOpacity - minOpacity))
                  }

                  const baseColor = '29,157,150'
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
                    ...(isToday ? { boxShadow: "0 0 0 2px #1d9d9680" } : {})
                  }

                  return (
                    <div key={i} className="flex-1 flex flex-col items-center min-w-0 h-full justify-end">
                      <span
                        className="text-xs font-medium text-muted-foreground tabular-nums shrink-0 w-full text-center"
                        style={{ marginBottom: 4, minHeight: 16 }}
                      >
                        {Number(payout).toFixed(0)}
                      </span>
                      <div
                        className="w-full rounded-t transition-all shrink-0"
                        style={style}
                      />
                    </div>
                  )
                })}
              </div>
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
