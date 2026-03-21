import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import VesselDashboard from './VesselDashboard'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'user-vo-001',
      currentVesselId: 'vessel-1',
    },
    refreshUser: vi.fn(),
  }),
}))

const dashboardPayload = {
  currentVessel: {
    id: 'vessel-1',
    displayName: 'Harbor Runner',
    socPercent: 61.2,
    dischargeRateKw: 32,
    capacityKwh: 61.2,
    maxCapacityKwh: 100,
  },
  activeContract: {
    id: 'contract-live-001',
    startTime: '2026-03-16T12:00:00.000Z',
    endTime: '2026-03-16T18:30:00.000Z',
    timeRemainingSeconds: 5400,
    timeWindowSeconds: 23400,
    estimatedEarnings: 52.75,
    energyAmountKwh: 120.0,
    drEventStatus: 'Active',
    station: {
      id: 'station-live-001',
      displayName: 'Halifax Marine Terminal',
      city: 'Halifax',
      provinceOrState: 'NS',
      latitude: 44.6488,
      longitude: -63.5752,
    },
    committedPowerKw: 30.0,
    energyDeliveredKwh: 44.4,
    energyRemainingKwh: 75.6,
  },
  metrics: {
    contractsCompleted: 4,
    totalKwhDischarged: 310.5,
    totalEarnings: 425.25,
  },
  weeklyEarnings: {
    total: 245.5,
    dailyEarnings: [0, 30, 42.5, 75, 98, 0, 0],
    todayIndex: 4,
  },
  updatedAt: '2026-03-16T17:00:00.000Z',
}

const socHistoryPayload = {
  currentVesselId: 'vessel-1',
  points: [
    { timestamp: '2026-03-15T12:00:00.000Z', socPercent: 66.4 },
    { timestamp: '2026-03-16T12:00:00.000Z', socPercent: 61.2 },
  ],
  empty: false,
  windowStart: '2026-03-09T12:00:00.000Z',
  windowEnd: '2026-03-16T12:00:00.000Z',
}

const contractsPayload = [
  {
    id: 'contract-history-001',
    vesselName: 'Harbor Runner',
    startTime: '2026-03-10T08:00:00.000Z',
    endTime: '2026-03-10T12:00:00.000Z',
    status: 'completed',
    energyAmount: 80,
    totalValue: 40,
    committedPowerKw: 20,
  },
]

const vesselsPayload = [
  {
    id: 'vessel-1',
    displayName: 'Harbor Runner',
    vesselType: 'ferry',
    chargerType: 'Type 2 AC',
    active: true,
    maxCapacity: 100,
    maxDischargeRate: 32,
  },
]

describe('VesselDashboard', () => {
  beforeEach(() => {
    localStorage.setItem('auth-token', 'test-token')
    vi.spyOn(window, 'setInterval').mockImplementation(() => 1)
    vi.spyOn(window, 'clearInterval').mockImplementation(() => {})
    global.fetch = vi.fn((input) => {
      const url = String(input)
      if (url.includes('/api/vo/dashboard')) {
        return Promise.resolve({
          ok: true,
          json: async () => dashboardPayload,
        })
      }
      if (url.includes('/api/vo/soc-history')) {
        return Promise.resolve({
          ok: true,
          json: async () => socHistoryPayload,
        })
      }
      if (url.includes('/api/contracts/my-contracts')) {
        return Promise.resolve({
          ok: true,
          json: async () => contractsPayload,
        })
      }
      if (url.includes('/api/vessels?userId=user-vo-001')) {
        return Promise.resolve({
          ok: true,
          json: async () => vesselsPayload,
        })
      }
      return Promise.reject(new Error(`Unhandled fetch: ${url}`))
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  test('renders live dashboard data instead of sample overrides', async () => {
    render(<VesselDashboard />)

    expect(await screen.findByText('Vessel Operator Dashboard')).toBeInTheDocument()
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/vo/dashboard'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      )
    })

    expect(await screen.findByText('Halifax Marine Terminal')).toBeInTheDocument()
    expect(screen.getByText('$245.50')).toBeInTheDocument()
    expect(screen.getByText('61.2%')).toBeInTheDocument()
    expect(screen.queryByText('Vancouver Marine Terminal')).not.toBeInTheDocument()
  })
})
