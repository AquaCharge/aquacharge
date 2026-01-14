import React, { useMemo, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import PortMap from './PortMap'

const viewModes = [
  { value: 'bookings', label: 'Bookings' },
  { value: 'nearby', label: 'Nearby' }
]

const PortMapCard = ({ bookings = [], isLoading = false, onBookingFocus = () => {} }) => {
  const [viewMode, setViewMode] = useState('bookings')

  const bookingsWithCoords = useMemo(
    () => bookings.filter((booking) => Number.isFinite(booking.lat) && Number.isFinite(booking.lng)),
    [bookings]
  )

  const upcomingBooking = useMemo(() => {
    if (!bookingsWithCoords.length) return null
    const now = new Date()
    const upcoming = bookingsWithCoords
      .filter((booking) => booking.startTime && booking.startTime > now)
      .sort((a, b) => a.startTime - b.startTime)
    return (upcoming[0] || bookingsWithCoords[0]) ?? null
  }, [bookingsWithCoords])

  const defaultCenter = upcomingBooking ? [upcomingBooking.lat, upcomingBooking.lng] : [20, 0]
  const defaultZoom = upcomingBooking ? 5 : 2

  return (
    <Card className="h-full">
      <CardHeader className="space-y-1">
        <CardTitle>Port Map</CardTitle>
        <CardDescription>Track booked ports and discover nearby charging locations.</CardDescription>
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <span className="text-sm text-muted-foreground">
            View mode:
          </span>
          <div className="inline-flex rounded-md border bg-muted p-1">
            {viewModes.map((mode) => (
              <Button
                key={mode.value}
                type="button"
                size="sm"
                variant={viewMode === mode.value ? 'default' : 'ghost'}
                className={`rounded-md px-3 py-1 text-sm ${
                  viewMode === mode.value ? 'bg-background shadow' : 'text-muted-foreground'
                }`}
                onClick={() => setViewMode(mode.value)}
              >
                {mode.label}
              </Button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <PortMap
          bookings={bookingsWithCoords}
          onBookingFocus={onBookingFocus}
          viewMode={viewMode}
          defaultCenter={defaultCenter}
          defaultZoom={defaultZoom}
        />
        {!bookingsWithCoords.length && !isLoading && (
          <p className="mt-3 text-sm text-muted-foreground">
            No bookings have location data yet. You can still pan around to explore available ports.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

export default PortMapCard
