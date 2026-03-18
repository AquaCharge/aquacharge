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
      contractId: 'contract-1',
      dischargeRateKw: 18,
      currentSoc: 54,
      timestamp: '2026-03-07T11:55:00+00:00',
    },
  ],
  vesselCurve: [
    {
      vesselId: 'vessel-1',
      contractId: 'contract-1',
      currentSoc: 54,
      latestDischargeRateKw: 18,
      totalEnergyDischargedKwh: 30,
      latestTimestamp: '2026-03-07T11:55:00+00:00',
      points: [
        { timestamp: '2026-03-07T11:40:00+00:00', energyDischargedKwh: 12, cumulativeEnergyDischargedKwh: 12, v2gContributionKw: 12 },
        { timestamp: '2026-03-07T11:50:00+00:00', energyDischargedKwh: 18, cumulativeEnergyDischargedKwh: 30, v2gContributionKw: 18 },
      ],
    },
  ],
  loadCurve: [
    { timestamp: '2026-03-07T11:40:00+00:00', energyDischargedKwh: 12, cumulativeEnergyDischargedKwh: 12, v2gContributionKw: 12, gridLoadWithoutV2GKw: null, gridLoadWithV2GKw: null },
    { timestamp: '2026-03-07T11:50:00+00:00', energyDischargedKwh: 18, cumulativeEnergyDischargedKwh: 30, v2gContributionKw: 18, gridLoadWithoutV2GKw: null, gridLoadWithV2GKw: null },
  ],
  baselineAvailable: false,
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
    // The component auto-sets filters.eventId from the first API response, which changes
    // queryString and triggers a second fetch (isLoading flips true again). Wait for both
    // loads to settle before asserting on content inside the isLoading conditional.
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/drevents/monitoring'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      )
      expect(global.fetch).toHaveBeenCalledTimes(2)
    })
    expect(screen.getByText('Dashboard refreshes automatically every 10 seconds.')).toBeInTheDocument()
    expect(screen.getByLabelText('Graph Filter')).toBeInTheDocument()
    expect(screen.getByText('Aggregate across 1 vessels')).toBeInTheDocument()
    expect(screen.getByText('30.00 kWh total')).toBeInTheDocument()
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
          vesselCurve: [],
          loadCurve: [],
          empty: true,
        }),
      })
    )

    render(<PowerDashboard />)

    expect(await screen.findByText('No telemetry has been recorded in the selected time window.')).toBeInTheDocument()
  })

  test('filters the graph to a selected vessel curve', async () => {
    const user = userEvent.setup()
    render(<PowerDashboard />)

    await screen.findByText('DR Monitoring Dashboard')
    const curveFilter = await screen.findByLabelText('Graph Filter')
    await user.selectOptions(curveFilter, 'vessel-1')

    expect(screen.getByText('Filtered to vessel-1')).toBeInTheDocument()
    expect(screen.getByText('Contract contract-1')).toBeInTheDocument()
    expect(screen.getAllByText('30.00 kWh').length).toBeGreaterThan(0)
  })
})
