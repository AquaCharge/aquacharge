// Reference "now" used consistently across all mock data generators
const NOW_REF = new Date('2026-03-21T18:00:00Z')

// Events ordered newest-first. Statuses and dates are chosen so that:
//   - Several Completed/Settled events fall inside the default 7-day window
//   - Older Archived events extend the picture when the period is widened
const SAMPLE_EVENTS = [
  {
    id: 'dr-evt-2026-0321',
    stationId: 'station-halifax-02',
    status: 'Active',
    targetEnergyKwh: 240,
    pricePerKwh: 0.30,
    startTime: '2026-03-21T12:00:00Z',
    endTime: '2026-03-21T17:00:00Z',
    regionLabel: 'Halifax, NS, Canada',
    maxParticipants: 7,
  },
  {
    id: 'dr-evt-2026-0320',
    stationId: 'station-moncton-01',
    status: 'Completed',
    targetEnergyKwh: 200,
    pricePerKwh: 0.27,
    startTime: '2026-03-20T09:00:00Z',
    endTime: '2026-03-20T13:00:00Z',
    regionLabel: 'Moncton, NB, Canada',
    maxParticipants: 6,
  },
  {
    id: 'dr-evt-2026-0318',
    stationId: 'station-halifax-01',
    status: 'Settled',
    targetEnergyKwh: 260,
    pricePerKwh: 0.28,
    startTime: '2026-03-18T14:00:00Z',
    endTime: '2026-03-18T18:00:00Z',
    regionLabel: 'Halifax, NS, Canada',
    maxParticipants: 8,
  },
  {
    id: 'dr-evt-2026-0316',
    stationId: 'station-vancouver-01',
    status: 'Completed',
    targetEnergyKwh: 180,
    pricePerKwh: 0.25,
    startTime: '2026-03-16T10:00:00Z',
    endTime: '2026-03-16T13:00:00Z',
    regionLabel: 'Vancouver, BC, Canada',
    maxParticipants: 5,
  },
  {
    id: 'dr-evt-2026-0312',
    stationId: 'station-moncton-01',
    status: 'Settled',
    targetEnergyKwh: 160,
    pricePerKwh: 0.25,
    startTime: '2026-03-12T10:00:00Z',
    endTime: '2026-03-12T12:00:00Z',
    regionLabel: 'Moncton, NB, Canada',
    maxParticipants: 5,
  },
  {
    id: 'dr-evt-2026-0307',
    stationId: 'station-halifax-02',
    status: 'Archived',
    targetEnergyKwh: 280,
    pricePerKwh: 0.30,
    startTime: '2026-03-07T15:00:00Z',
    endTime: '2026-03-07T19:00:00Z',
    regionLabel: 'Halifax, NS, Canada',
    maxParticipants: 8,
  },
  {
    id: 'dr-evt-2026-0301',
    stationId: 'station-halifax-01',
    status: 'Archived',
    targetEnergyKwh: 220,
    pricePerKwh: 0.28,
    startTime: '2026-03-01T09:00:00Z',
    endTime: '2026-03-01T13:00:00Z',
    regionLabel: 'Halifax, NS, Canada',
    maxParticipants: 6,
  },
]

// Mock contracts corresponding to the sample events above.
// totalValue = energyAmount * pricePerKwh for each event's price.
// endTime matches the parent event's endTime so period filtering works correctly.
const MOCK_CONTRACTS = [
  // dr-evt-2026-0321 — Active (today), 2 active contracts, not yet settled
  { id: 'c-0321a', drEventId: 'dr-evt-2026-0321', status: 'active',     totalValue: 25.20, energyAmount:  84, endTime: '2026-03-21T17:00:00Z' },
  { id: 'c-0321b', drEventId: 'dr-evt-2026-0321', status: 'active',     totalValue: 25.20, energyAmount:  84, endTime: '2026-03-21T17:00:00Z' },

  // dr-evt-2026-0320 — Completed Mar 20: 2 contracts × 78 kWh × $0.27 = $21.06 each
  { id: 'c-0320a', drEventId: 'dr-evt-2026-0320', status: 'completed',  totalValue: 21.06, energyAmount:  78, endTime: '2026-03-20T13:00:00Z' },
  { id: 'c-0320b', drEventId: 'dr-evt-2026-0320', status: 'completed',  totalValue: 21.06, energyAmount:  78, endTime: '2026-03-20T13:00:00Z' },

  // dr-evt-2026-0318 — Settled Mar 18: 3 contracts × 78 kWh × $0.28 = $21.84 each
  { id: 'c-0318a', drEventId: 'dr-evt-2026-0318', status: 'completed',  totalValue: 21.84, energyAmount:  78, endTime: '2026-03-18T18:00:00Z' },
  { id: 'c-0318b', drEventId: 'dr-evt-2026-0318', status: 'completed',  totalValue: 21.84, energyAmount:  78, endTime: '2026-03-18T18:00:00Z' },
  { id: 'c-0318c', drEventId: 'dr-evt-2026-0318', status: 'completed',  totalValue: 21.84, energyAmount:  78, endTime: '2026-03-18T18:00:00Z' },

  // dr-evt-2026-0316 — Completed Mar 16: 2 contracts × 76.5 kWh × $0.25 = $19.13 each
  { id: 'c-0316a', drEventId: 'dr-evt-2026-0316', status: 'completed',  totalValue: 19.13, energyAmount:  76.5, endTime: '2026-03-16T13:00:00Z' },
  { id: 'c-0316b', drEventId: 'dr-evt-2026-0316', status: 'completed',  totalValue: 19.13, energyAmount:  76.5, endTime: '2026-03-16T13:00:00Z' },

  // dr-evt-2026-0312 — Settled Mar 12 (outside 7-day, inside 14-day): 2 × 108.8 kWh × $0.25 = $27.20
  { id: 'c-0312a', drEventId: 'dr-evt-2026-0312', status: 'completed',  totalValue: 27.20, energyAmount: 108.8, endTime: '2026-03-12T12:00:00Z' },
  { id: 'c-0312b', drEventId: 'dr-evt-2026-0312', status: 'completed',  totalValue: 27.20, energyAmount: 108.8, endTime: '2026-03-12T12:00:00Z' },

  // dr-evt-2026-0307 — Archived Mar 7 (inside 30-day): 2 × 128 kWh × $0.30 = $38.40
  { id: 'c-0307a', drEventId: 'dr-evt-2026-0307', status: 'completed',  totalValue: 38.40, energyAmount: 128,  endTime: '2026-03-07T19:00:00Z' },
  { id: 'c-0307b', drEventId: 'dr-evt-2026-0307', status: 'completed',  totalValue: 38.40, energyAmount: 128,  endTime: '2026-03-07T19:00:00Z' },

  // dr-evt-2026-0301 — Archived Mar 1 (inside 30-day): 2 × 90.25 kWh × $0.28 = $25.27
  { id: 'c-0301a', drEventId: 'dr-evt-2026-0301', status: 'completed',  totalValue: 25.27, energyAmount:  90.25, endTime: '2026-03-01T13:00:00Z' },
  { id: 'c-0301b', drEventId: 'dr-evt-2026-0301', status: 'completed',  totalValue: 25.27, energyAmount:  90.25, endTime: '2026-03-01T13:00:00Z' },
]

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const HEATMAP_BANDS = ['00-04', '04-08', '08-12', '12-18', '18-24']

const getHoursToShow = (periodHours, grain) => {
  const parsed = Number(periodHours || 168)
  if (!Number.isFinite(parsed) || parsed < 1) return grain === 'hour' ? 24 : 7
  return grain === 'hour'
    ? Math.min(parsed, 336)
    : Math.max(3, Math.ceil(Math.min(parsed, 720) / 24))
}

const buildSeries = ({ periodHours, grain }) => {
  const count = getHoursToShow(periodHours, grain)
  const bucketMs = grain === 'hour' ? 60 * 60 * 1000 : 24 * 60 * 60 * 1000
  const now = NOW_REF.getTime()
  const start = now - (count - 1) * bucketMs

  return Array.from({ length: count }, (_, index) => {
    const timestamp = new Date(start + index * bucketMs).toISOString()
    const wave = 18 + Math.sin(index / 2.1) * 7 + (index % 4) * 1.25
    const energy = Math.max(6, wave + (grain === 'hour' ? 0 : 8))
    const avgPower = Math.max(4, energy * 0.78 + ((index + 1) % 3))
    return {
      timestamp,
      energyDischargedKwh: Number(energy.toFixed(2)),
      averagePowerKw: Number(avgPower.toFixed(2)),
    }
  })
}

const buildHeatmap = () =>
  DAY_LABELS.map((dayLabel, dayIndex) => ({
    dayLabel,
    bands: HEATMAP_BANDS.map((label, bandIndex) => {
      const base = 10 + dayIndex * 1.1 + bandIndex * 2.7
      const value = base + (dayIndex % 2 === 0 ? 1.8 : 0.9)
      return {
        label,
        averagePowerKw: Number(value.toFixed(1)),
      }
    }),
  }))

const buildStatusDistribution = (events) => {
  const counts = events.reduce((acc, event) => {
    const key = event.status || 'Unknown'
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0) || 1
  return Object.entries(counts)
    .map(([status, count]) => ({
      status,
      count,
      percent: Number(((count / total) * 100).toFixed(2)),
    }))
    .sort((a, b) => b.count - a.count)
}

const buildFinancials = (availableEvents, filters) => {
  const periodHours = Number(filters.periodHours || 168)
  const grain = filters.grain || 'day'
  const bucketMs = grain === 'hour' ? 60 * 60 * 1000 : 24 * 60 * 60 * 1000
  const periodStartMs = NOW_REF.getTime() - periodHours * 60 * 60 * 1000
  const eventIds = new Set(availableEvents.map((ev) => ev.id))

  // Filter contracts to this period and these events
  const periodContracts = MOCK_CONTRACTS.filter((c) => {
    if (!eventIds.has(c.drEventId)) return false
    const endMs = new Date(c.endTime).getTime()
    return endMs >= periodStartMs && endMs <= NOW_REF.getTime()
  })

  const completedContracts = periodContracts.filter((c) => c.status === 'completed')
  const pendingOrActiveContracts = periodContracts.filter((c) => c.status === 'active' || c.status === 'pending')

  const totalPayoutUsd = Number(
    completedContracts.reduce((sum, c) => sum + Number(c.totalValue || 0), 0).toFixed(2)
  )
  const committedExposureUsd = Number(
    pendingOrActiveContracts.reduce((sum, c) => sum + Number(c.totalValue || 0), 0).toFixed(2)
  )

  const totalCompletedEnergyKwh = completedContracts.reduce(
    (sum, c) => sum + Number(c.energyAmount || 0),
    0
  )
  const costPerKwhUsd =
    totalPayoutUsd > 0 && totalCompletedEnergyKwh > 0
      ? Number((totalPayoutUsd / totalCompletedEnergyKwh).toFixed(4))
      : null

  // Weighted avg price across available events
  const { weightedSum, totalKwh } = availableEvents.reduce(
    (acc, ev) => {
      const kwh = Number(ev.targetEnergyKwh || 0)
      const price = Number(ev.pricePerKwh || 0)
      if (kwh > 0) {
        acc.weightedSum += price * kwh
        acc.totalKwh += kwh
      }
      return acc
    },
    { weightedSum: 0, totalKwh: 0 }
  )
  const avgPricePerKwhUsd = totalKwh > 0 ? Number((weightedSum / totalKwh).toFixed(4)) : null

  // Financial time series: bucket completed contract payouts by grain using endTime
  const buckets = {}
  for (const c of completedContracts) {
    const endMs = new Date(c.endTime).getTime()
    const bucketKey = new Date(endMs - (endMs % bucketMs)).toISOString()
    buckets[bucketKey] = Number(((buckets[bucketKey] || 0) + Number(c.totalValue || 0)).toFixed(2))
  }
  const financialTimeSeries = Object.entries(buckets)
    .map(([timestamp, payoutUsd]) => ({ timestamp, payoutUsd }))
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

  // Event breakdown: per-event target value vs. actual payout from completed contracts
  const payoutByEvent = completedContracts.reduce((acc, c) => {
    acc[c.drEventId] = Number(((acc[c.drEventId] || 0) + Number(c.totalValue || 0)).toFixed(2))
    return acc
  }, {})
  const eventBreakdown = availableEvents
    .map((ev) => {
      const targetValueUsd = Number(((ev.targetEnergyKwh || 0) * (ev.pricePerKwh || 0)).toFixed(2))
      const actualPayoutUsd = payoutByEvent[ev.id] || 0
      const deliveryRatePct =
        targetValueUsd > 0 ? Number(((actualPayoutUsd / targetValueUsd) * 100).toFixed(2)) : 0
      return {
        eventId: ev.id,
        startTime: ev.startTime,
        targetValueUsd,
        actualPayoutUsd,
        deliveryRatePct,
      }
    })
    .sort((a, b) => new Date(b.startTime) - new Date(a.startTime))

  return {
    totalPayoutUsd,
    committedExposureUsd,
    costPerKwhUsd,
    avgPricePerKwhUsd,
    timeSeries: financialTimeSeries,
    eventBreakdown,
  }
}

// Returns weekly payout data for ALL DR events (last 7 days), bucketed by day of week.
// Shape matches the VO weeklyEarnings object so WeeklyPayoutsCard can use identical rendering logic.
export const getMockPSOWeeklyPayouts = () => {
  const weekStartMs = NOW_REF.getTime() - 6 * 24 * 60 * 60 * 1000 // 7-day window: [NOW_REF-6d, NOW_REF]
  const daily = [0, 0, 0, 0, 0, 0, 0] // Mon=0 … Sun=6

  for (const c of MOCK_CONTRACTS) {
    if (c.status !== 'completed') continue
    const endMs = new Date(c.endTime).getTime()
    if (endMs < weekStartMs || endMs > NOW_REF.getTime()) continue
    const weekday = new Date(c.endTime).getUTCDay() // 0=Sun … 6=Sat
    // Convert JS Sunday-first (0=Sun) to Mon-first (0=Mon)
    const index = weekday === 0 ? 6 : weekday - 1
    daily[index] = Number((daily[index] + Number(c.totalValue || 0)).toFixed(2))
  }

  return {
    total: Number(daily.reduce((sum, v) => sum + v, 0).toFixed(2)),
    dailyPayouts: daily,
  }
}

export const getMockPSOAnalyticsSnapshot = (filters = {}) => {
  const regionQuery = String(filters.region || '').trim().toLowerCase()
  let availableEvents = SAMPLE_EVENTS
  if (regionQuery) {
    availableEvents = availableEvents.filter((event) =>
      event.regionLabel.toLowerCase().includes(regionQuery)
    )
  }
  const selectedEvent =
    availableEvents.find((event) => event.id === filters.eventId) || availableEvents[0] || null

  const timeSeries = buildSeries(filters)
  const totalEnergy = timeSeries.reduce((sum, point) => sum + Number(point.energyDischargedKwh || 0), 0)
  const avgPower =
    timeSeries.reduce((sum, point) => sum + Number(point.averagePowerKw || 0), 0) /
    Math.max(timeSeries.length, 1)
  const peakPower = Math.max(...timeSeries.map((point) => Number(point.averagePowerKw || 0)), 0)
  const eventsConsidered = availableEvents.length
  const maxParticipants = availableEvents.reduce((sum, event) => sum + Number(event.maxParticipants || 0), 0)
  const distinctVessels = 7

  return {
    filters: {
      eventId: selectedEvent?.id || null,
      region: filters.region || '',
      periodHours: Number(filters.periodHours || 168),
      grain: filters.grain || 'day',
    },
    summary: {
      totalEnergyDischargedKwh: Number(totalEnergy.toFixed(2)),
      averagePowerKw: Number(avgPower.toFixed(2)),
      peakPowerKw: Number(peakPower.toFixed(2)),
      completionRatePercent: 68.4,
      participationRatePercent: Number(
        ((distinctVessels / Math.max(maxParticipants, 1)) * 100).toFixed(2)
      ),
      eventsConsidered,
      contractsConsidered: 34,
      baselineAvailable: false,
    },
    selectedEvent,
    timeSeries,
    statusDistribution: buildStatusDistribution(availableEvents),
    heatmap: buildHeatmap(),
    financials: buildFinancials(availableEvents, filters),
    availableEvents,
    empty: false,
    updatedAt: NOW_REF.toISOString(),
  }
}
