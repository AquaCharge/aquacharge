import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'

import ContractBookingFlow from './ContractBookingFlow'

const contract = {
  id: 'contract-1',
  vesselId: 'vessel-1',
  vesselName: 'Sea Breeze',
  committedPowerKw: 25,
  pricePerKwh: 0.24,
}

const bookingContext = {
  stationId: 'station-1',
  startTime: '2026-03-25T10:00:00+00:00',
  endTime: '2026-03-25T12:00:00+00:00',
  availableSlots: [
    {
      chargerId: 'charger-1',
      chargerType: 'Type 2 AC',
      maxRate: 22,
      available: true,
    },
    {
      chargerId: 'charger-2',
      chargerType: 'Type 2 AC',
      maxRate: 11,
      available: false,
    },
  ],
}

describe('ContractBookingFlow', () => {
  beforeEach(() => {
    vi.spyOn(window, 'setInterval').mockImplementation(() => 1)
    vi.spyOn(window, 'clearInterval').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('submits a successful booking', async () => {
    const user = userEvent.setup()
    const onBookingComplete = vi.fn()
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: async () => ({
          id: 'booking-1',
          chargerId: 'charger-1',
          startTime: bookingContext.startTime,
          endTime: bookingContext.endTime,
        }),
      })
    )

    render(
      <ContractBookingFlow
        authToken="test-token"
        contract={contract}
        bookingContext={bookingContext}
        onBookingComplete={onBookingComplete}
        onDismiss={() => {}}
      />
    )

    await user.click(screen.getByRole('button', { name: /confirm booking/i }))

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/bookings'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
          body: expect.stringContaining('"chargerId":"charger-1"'),
        })
      )
    })
    expect(await screen.findByText('Booking confirmed')).toBeInTheDocument()
    expect(onBookingComplete).toHaveBeenCalledWith(
      expect.objectContaining({ id: 'booking-1' })
    )
  })

  test('shows a conflict error and refreshes availability', async () => {
    const user = userEvent.setup()
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ error: 'Time slot conflicts with existing booking' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          stationId: bookingContext.stationId,
          startTime: bookingContext.startTime,
          endTime: bookingContext.endTime,
          chargers: bookingContext.availableSlots,
        }),
      })

    render(
      <ContractBookingFlow
        authToken="test-token"
        contract={contract}
        bookingContext={bookingContext}
        onBookingComplete={() => {}}
        onDismiss={() => {}}
      />
    )

    await user.click(screen.getByRole('button', { name: /confirm booking/i }))

    expect(
      await screen.findByText('Time slot conflicts with existing booking')
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledTimes(2)
      expect(global.fetch).toHaveBeenLastCalledWith(
        expect.stringContaining('/api/stations/station-1/available-slots'),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: 'Bearer test-token',
          }),
        })
      )
    })
  })

  test('shows unavailable-slot messaging when no chargers are open', () => {
    render(
      <ContractBookingFlow
        authToken="test-token"
        contract={contract}
        bookingContext={{
          ...bookingContext,
          availableSlots: bookingContext.availableSlots.map((slot) => ({
            ...slot,
            available: false,
          })),
        }}
        onBookingComplete={() => {}}
        onDismiss={() => {}}
      />
    )

    expect(screen.getByText('No dispatchable chargers right now')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /confirm booking/i })
    ).toBeDisabled()
  })
})
