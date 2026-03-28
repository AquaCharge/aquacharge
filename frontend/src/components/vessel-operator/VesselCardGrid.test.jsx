import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, test } from 'vitest'

import { VesselCardGrid } from './VesselCardGrid'

describe('VesselCardGrid', () => {
  test('uses telemetry-backed SoC for current charge while showing full battery capacity', () => {
    render(
      <VesselCardGrid
        vessels={[
          {
            id: 'vessel-1',
            displayName: 'Harbor Spirit',
            vesselType: 'electric_ferry',
            chargerType: 'CCS',
            active: true,
            capacity: 96,
            maxCapacity: 120,
            currentSoc: 44,
            maxChargeRate: 48,
            minChargeRate: 12,
            maxDischargeRate: 48,
            rangeMeters: 12000,
            latitude: 45.0,
            longitude: -63.0,
            createdAt: '2026-03-28T12:00:00.000Z',
            updatedAt: '2026-03-28T13:00:00.000Z',
          },
        ]}
      />
    )

    expect(screen.getByText('120.0 kWh')).toBeInTheDocument()
    expect(screen.getByText('44%')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Harbor Spirit'))

    expect(screen.getAllByText('Battery Capacity').length).toBeGreaterThan(1)
    expect(screen.getByText('Current Charge')).toBeInTheDocument()
    expect(screen.getAllByText('120.0 kWh').length).toBeGreaterThan(0)
    expect(screen.getByText('52.8 kWh')).toBeInTheDocument()
  })
})
