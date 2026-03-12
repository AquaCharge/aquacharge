import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { FileCheck, Zap, Wallet } from 'lucide-react'

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export const MetricCard = ({ title, value, helper, loading }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
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
      <CardTitle className="text-sm font-medium">State of charge</CardTitle>
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
        <CardTitle className="text-sm font-medium">All Time</CardTitle>
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
  const daily = weeklyEarnings?.dailyEarnings ?? [0, 0, 0, 0, 0, 0, 0]
  const total = weeklyEarnings?.total ?? 0
  const todayIndex = weeklyEarnings?.todayIndex ?? 0
  const maxEarnings = Math.max(1, ...daily)

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-0">
        <CardTitle className="text-sm font-light">Earnings</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <>
            <Skeleton className="h-8 w-24 mb-4" />
            <Skeleton className="h-24 w-full" />
          </>
        ) : (
          <>
            <div className="text-2xl font-bold mb-1">
              ${Number(total).toFixed(2)}
            </div>
            <p className="text-xs text-muted-foreground mb-4">This week</p>
            <div className="flex items-end gap-1 h-24">
              {daily.map((earnings, i) => {
                const isToday = i === todayIndex
                const barHeightPx = maxEarnings > 0 && earnings > 0
                  ? Math.max(2, (earnings / maxEarnings) * 48)
                  : 0
                return (
                  <div key={i} className="flex-1 flex flex-col items-center min-w-0 h-full">
                    <div className="flex-1 min-h-0 w-full" />
                    <span
                      className="text-xs font-medium text-muted-foreground tabular-nums shrink-0 w-full text-center"
                      style={{ marginBottom: 5 }}
                    >
                      {earnings > 0 ? Number(earnings).toFixed(0) : ''}
                    </span>
                    <div
                      className={`w-full rounded-t transition-all shrink-0`}
                      style={{ height: barHeightPx, backgroundColor: isToday ? '#1D9D96' : 'rgba(29, 157, 150, 0.6)' }}
                    />
                    <span
                      className={`text-xs shrink-0 ${isToday ? 'font-semibold text-foreground' : 'text-muted-foreground'}`}
                    >
                      {DAY_LABELS[i]}
                    </span>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
