import { useEffect, useState } from 'react'
import { AlertCircle, CheckCircle2, Clock3, MapPin, RefreshCw, Zap } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { getApiEndpoint } from '@/config/api'

const POLL_INTERVAL_MS = 5000

const formatDateTime = (value) => {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

const formatRate = (value) => {
  if (value == null || value === '') return '—'
  return `${value} kW`
}

const ContractBookingFlow = ({
  authToken,
  contract,
  bookingContext,
  onBookingComplete,
  onDismiss,
}) => {
  const [availability, setAvailability] = useState(bookingContext)
  const [selectedChargerId, setSelectedChargerId] = useState('')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [successBooking, setSuccessBooking] = useState(null)

  const availableSlots = availability?.availableSlots || []
  const availableChargers = availableSlots.filter((slot) => slot.available)

  useEffect(() => {
    setAvailability(bookingContext)
  }, [bookingContext])

  useEffect(() => {
    if (!availableChargers.length) {
      setSelectedChargerId('')
      return
    }

    const stillAvailable = availableChargers.some(
      (slot) => slot.chargerId === selectedChargerId
    )
    if (!stillAvailable) {
      setSelectedChargerId(availableChargers[0].chargerId)
    }
  }, [availableChargers, selectedChargerId])

  useEffect(() => {
    if (!authToken || !availability?.stationId || !availability?.startTime || !availability?.endTime) {
      return undefined
    }

    const refreshAvailability = async (background = false) => {
      if (!background) {
        setIsRefreshing(true)
      }
      try {
        const params = new URLSearchParams({
          start: availability.startTime,
          end: availability.endTime,
        })
        const response = await fetch(
          getApiEndpoint(
            `/api/stations/${availability.stationId}/available-slots?${params.toString()}`
          ),
          {
            headers: { Authorization: `Bearer ${authToken}` },
          }
        )
        if (!response.ok) {
          const payload = await response.json().catch(() => ({}))
          throw new Error(payload.error || 'Failed to refresh charger availability')
        }
        const data = await response.json()
        setAvailability({
          stationId: data.stationId,
          startTime: data.startTime,
          endTime: data.endTime,
          availableSlots: Array.isArray(data.chargers) ? data.chargers : [],
        })
      } catch (refreshError) {
        setError(refreshError.message || 'Unable to refresh charger availability.')
      } finally {
        if (!background) {
          setIsRefreshing(false)
        }
      }
    }

    const intervalId = window.setInterval(() => {
      refreshAvailability(true)
    }, POLL_INTERVAL_MS)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [authToken, availability?.endTime, availability?.startTime, availability?.stationId])

  const handleManualRefresh = async () => {
    setIsRefreshing(true)
    try {
      const params = new URLSearchParams({
        start: availability.startTime,
        end: availability.endTime,
      })
      const response = await fetch(
        getApiEndpoint(
          `/api/stations/${availability.stationId}/available-slots?${params.toString()}`
        ),
        {
          headers: { Authorization: `Bearer ${authToken}` },
        }
      )
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || 'Failed to refresh charger availability')
      }
      const data = await response.json()
      setAvailability({
        stationId: data.stationId,
        startTime: data.startTime,
        endTime: data.endTime,
        availableSlots: Array.isArray(data.chargers) ? data.chargers : [],
      })
    } catch (refreshError) {
      setError(refreshError.message || 'Unable to refresh charger availability.')
    } finally {
      setIsRefreshing(false)
    }
  }

  const handleBooking = async () => {
    if (!selectedChargerId) {
      setError('Select an available charger before confirming the booking.')
      return
    }

    setError('')
    setIsSubmitting(true)
    try {
      const response = await fetch(getApiEndpoint('/api/bookings'), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          vesselId: contract.vesselId,
          stationId: availability.stationId,
          chargerId: selectedChargerId,
          startTime: availability.startTime,
          endTime: availability.endTime,
          contractId: contract.id,
        }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || 'Failed to create the booking')
      }

      const booking = await response.json()
      setSuccessBooking(booking)
      onBookingComplete?.(booking)
    } catch (bookingError) {
      setError(bookingError.message || 'Unable to complete the booking.')
      await handleManualRefresh()
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!contract || !availability) return null

  return (
    <Card className="border-blue-200 shadow-sm">
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2 text-xl">
            <Zap className="h-5 w-5 text-blue-600" />
            Complete Charger Booking
          </CardTitle>
          <CardDescription>
            Contract accepted for {contract.vesselName}. Pick a charger to reserve the dispatch
            window.
          </CardDescription>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleManualRefresh} disabled={isRefreshing}>
            <RefreshCw className={`mr-2 h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            Dismiss
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {availability?.warning && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            {availability.warning}
          </div>
        )}

        {successBooking && (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            <div className="mb-2 flex items-center gap-2 font-medium">
              <CheckCircle2 className="h-4 w-4" />
              Booking confirmed
            </div>
            <div>Booking ID: {successBooking.id}</div>
            <div>Charger: {successBooking.chargerId}</div>
            <div>
              Window: {formatDateTime(successBooking.startTime)} to{' '}
              {formatDateTime(successBooking.endTime)}
            </div>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1.8fr)]">
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 flex items-center gap-2 text-sm font-medium text-slate-700">
              <MapPin className="h-4 w-4" />
              Dispatch Summary
            </div>
            <div className="space-y-2 text-sm text-slate-600">
              <div>Contract: {contract.id}</div>
              <div>Station: {availability.stationId}</div>
              <div>Start: {formatDateTime(availability.startTime)}</div>
              <div>End: {formatDateTime(availability.endTime)}</div>
              <div>Committed power: {contract.committedPowerKw || '—'} kW</div>
              <div>Compensation: ${contract.pricePerKwh}/kWh</div>
            </div>

            <div className="mt-4 flex items-center gap-2 text-xs text-slate-500">
              <Clock3 className="h-4 w-4" />
              Availability auto-refreshes every 5 seconds.
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-slate-900">Available Chargers</h3>
                <p className="text-sm text-slate-500">
                  {availableChargers.length} of {availableSlots.length} chargers available
                </p>
              </div>
              <Badge variant="outline">{availableChargers.length} open</Badge>
            </div>

            {availableSlots.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 p-5 text-sm text-slate-500">
                No chargers are configured for this station yet.
              </div>
            ) : (
              <div className="space-y-3">
                {availableSlots.map((slot) => {
                  const isSelected = slot.chargerId === selectedChargerId
                  return (
                    <button
                      key={slot.chargerId}
                      type="button"
                      className={`w-full rounded-xl border p-4 text-left transition ${
                        slot.available
                          ? isSelected
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-slate-200 hover:border-blue-300 hover:bg-slate-50'
                          : 'cursor-not-allowed border-slate-200 bg-slate-100 opacity-70'
                      }`}
                      disabled={!slot.available || isSubmitting || !!successBooking}
                      onClick={() => setSelectedChargerId(slot.chargerId)}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="font-medium text-slate-900">{slot.chargerId}</div>
                          <div className="mt-1 text-sm text-slate-600">
                            {slot.chargerType || 'Unknown type'} · Max {formatRate(slot.maxRate)}
                          </div>
                        </div>
                        <Badge
                          className={
                            slot.available
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-200 text-slate-700'
                          }
                        >
                          {slot.available ? 'Available' : 'Unavailable'}
                        </Badge>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}

            {!availableChargers.length && (
              <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                <div className="mb-1 flex items-center gap-2 font-medium">
                  <AlertCircle className="h-4 w-4" />
                  No dispatchable chargers right now
                </div>
                Refresh to check again or dismiss this panel and retry later.
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={onDismiss} disabled={isSubmitting}>
                Close
              </Button>
              <Button
                className="bg-blue-600 text-white hover:bg-blue-700"
                onClick={handleBooking}
                disabled={!selectedChargerId || isSubmitting || !!successBooking}
              >
                {isSubmitting ? 'Confirming…' : 'Confirm Booking'}
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default ContractBookingFlow
