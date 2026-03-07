import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import PowerDashboard from './PowerDashboard'

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      type_name: 'POWER_OPERATOR',
    },
  }),
}))

const monitoringPayload = {
  filters: {
    eventId: 'event-1',
    region: '',
    periodHours: 24,
  },
  selectedEvent: {
    id: 'event-1',
    stationId: 'station-1',
    status: 'Active',
    targetEnergyKwh: 200,
    startTime: '2026-03-07T10:00:00+00:00',
    endTime: '2026-03-07T12:00:00+00:00',
    regionLabel: 'Moncton, NB, Canada',
  },
  summary: {
    totalEnergyDeliveredKwh: 90,
    progressPercent: 45,
    activeVessels: 2,
    eventStatus: 'Active',
    targetEnergyKwh: 200,
  },
  vesselRates: [
    {
      vesselId: 'vessel-1',
      dischargeRateKw: 18,
      currentSoc: 54,
      timestamp: '2026-03-07T11:55:00+00:00',
    },
  ],
  dischargeSeries: {
    allVessels: [
      { timestamp: '2026-03-07T11:40:00+00:00', powerKw: 12 },
      { timestamp: '2026-03-07T11:50:00+00:00', powerKw: 18 },
    ],
    vessels: [
      {
        vesselId: 'vessel-1',
        currentSoc: 54,
        latestDischargeRateKw: 18,
        series: [
          { timestamp: '2026-03-07T11:40:00+00:00', powerKw: 12 },
          { timestamp: '2026-03-07T11:50:00+00:00', powerKw: 18 },
        ],
      },
    ],
  },
  availableEvents: [
    {
      id: 'event-1',
      stationId: 'station-1',
      status: 'Active',
      startTime: '2026-03-07T10:00:00+00:00',
      endTime: '2026-03-07T12:00:00+00:00',
      targetEnergyKwh: 200,
      regionLabel: 'Moncton, NB, Canada',
    },
  ],
  empty: false,
  updatedAt: '2026-03-07T11:56:00+00:00',
}

describe('PowerDashboard', () => {
  beforeEach(() => {
    localStorage.setItem('auth-token', 'test-token')
    vi.spyOn(window, 'setInterval').mockImplementation(() => 1)
    vi.spyOn(window, 'clearInterval').mockImplementation(() => {})
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: async () => monitoringPayload,
      })
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  test('renders monitoring metrics from API data', async () => {
    render(<PowerDashboard />)

    expect(await screen.findByText('DR Monitoring Dashboard')).toBeInTheDocument()
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/drevents/monitoring'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      )
    })
    expect(screen.getByText('Dashboard refreshes automatically every 10 seconds.')).toBeInTheDocument()
    expect(screen.getByText('Individual Vessel Discharge Rates')).toBeInTheDocument()
    expect(screen.getByText('Discharge Over Time')).toBeInTheDocument()
  })

  test('applies region filter and refetches dashboard data', async () => {
    const user = userEvent.setup()
    render(<PowerDashboard />)

    await screen.findByText('DR Monitoring Dashboard')
    const regionInput = screen.getByLabelText('Geographic Region')
    await user.clear(regionInput)
    await user.type(regionInput, 'Moncton')

    await waitFor(() => {
      expect(global.fetch).toHaveBeenLastCalledWith(
        expect.stringContaining('region=Moncton'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      )
    })
  })

  test('shows empty state when no telemetry is available', async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({
          ...monitoringPayload,
          summary: {
            ...monitoringPayload.summary,
            totalEnergyDeliveredKwh: 0,
            progressPercent: 0,
            activeVessels: 0,
          },
          vesselRates: [],
          dischargeSeries: {
            allVessels: [],
            vessels: [],
          },
          empty: true,
        }),
      })
    )

    render(<PowerDashboard />)

    expect(await screen.findByText('No telemetry has been recorded in the selected time window.')).toBeInTheDocument()
    expect(screen.getByText('No vessel discharge measurements matched the current filters.')).toBeInTheDocument()
  })
})
