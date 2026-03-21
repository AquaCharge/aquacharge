import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import Analytics from './Analytics'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      type_name: 'POWER_OPERATOR',
    },
  }),
}))

vi.mock('@/components/ui/PSOAnalytics', () => ({
  DispatchHeatmap: () => <div>DispatchHeatmap</div>,
  EnergyTrendChart: () => <div>EnergyTrendChart</div>,
  EventValueChart: () => <div>EventValueChart</div>,
  FinancialTrendChart: () => <div>FinancialTrendChart</div>,
  StatusMix: () => <div>StatusMix</div>,
}))

const analyticsPayload = {
  filters: {
    eventId: 'event-1',
    region: '',
    periodHours: 168,
    grain: 'day',
  },
  summary: {
    totalEnergyDischargedKwh: 60,
    averagePowerKw: 10,
    peakPowerKw: 18,
    completionRatePercent: 50,
    participationRatePercent: 25,
    eventsConsidered: 1,
    contractsConsidered: 2,
    baselineAvailable: false,
  },
  selectedEvent: {
    id: 'event-1',
    stationId: 'station-1',
    status: 'Active',
    targetEnergyKwh: 200,
    startTime: '2026-03-07T10:00:00+00:00',
    endTime: '2026-03-07T12:00:00+00:00',
    regionLabel: 'Halifax, NS, Canada',
  },
  timeSeries: [{ timestamp: '2026-03-07T00:00:00+00:00', energyDischargedKwh: 60, averagePowerKw: 10 }],
  statusDistribution: [{ status: 'Active', count: 1, percent: 100 }],
  vesselLeaderboard: [],
  heatmap: [],
  availableEvents: [
    {
      id: 'event-1',
      stationId: 'station-1',
      status: 'Active',
      startTime: '2026-03-07T10:00:00+00:00',
      endTime: '2026-03-07T12:00:00+00:00',
      targetEnergyKwh: 200,
      regionLabel: 'Halifax, NS, Canada',
    },
  ],
  financials: {
    totalPayoutUsd: 80,
    committedExposureUsd: 20,
    costPerKwhUsd: 1.3333,
    avgPricePerKwhUsd: 0.4,
    timeSeries: [{ timestamp: '2026-03-07T00:00:00+00:00', payoutUsd: 80 }],
    eventBreakdown: [
      {
        eventId: 'event-1',
        startTime: '2026-03-07T10:00:00+00:00',
        targetValueUsd: 80,
        actualPayoutUsd: 80,
        deliveryRatePct: 100,
      },
    ],
  },
  empty: false,
  updatedAt: '2026-03-07T12:00:00+00:00',
}

describe('Analytics', () => {
  beforeEach(() => {
    localStorage.setItem('auth-token', 'test-token')
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: async () => analyticsPayload,
      })
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  test('loads live analytics data by default', async () => {
    render(<Analytics />)

    expect(await screen.findByText('Historical Analytics')).toBeInTheDocument()
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/drevents/analytics'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      )
    })

    expect(screen.getByText('Historical Analytics')).toBeInTheDocument()
    expect(screen.getByText('DispatchHeatmap')).toBeInTheDocument()
    expect(
      screen.getByRole('option', {
        name: 'event-1 · Active · Halifax, NS, Canada',
      })
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: /use sample data|using sample data/i })
    ).not.toBeInTheDocument()
  })
})
