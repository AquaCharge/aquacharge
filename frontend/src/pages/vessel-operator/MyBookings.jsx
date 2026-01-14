import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Calendar, Clock, MapPin, Zap } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import PortMapCard from '@/components/vessel-operator/PortMapCard'
import { getApiEndpoint } from '@/config/api'

const STATUS_LABELS = {
  1: 'pending',
  2: 'confirmed',
  3: 'completed',
  4: 'cancelled'
}

const formatDate = (value) => {
  if (!value) return 'TBD'
  return value.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })
}

const formatTimeRange = (start, end) => {
  if (!start || !end) return 'TBD'
  const startText = start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const endText = end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  return `${startText} - ${endText}`
}

const mapStatus = (value) => {
  if (typeof value === 'string') return value.toLowerCase()
  return STATUS_LABELS[value] || 'pending'
}

const getStatusColors = (status) => {
  switch (status) {
    case 'confirmed':
      return 'bg-emerald-100 text-emerald-800'
    case 'pending':
      return 'bg-amber-100 text-amber-800'
    case 'completed':
      return 'bg-slate-100 text-slate-800'
    case 'cancelled':
      return 'bg-rose-100 text-rose-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const MyBookings = () => {
  const [bookings, setBookings] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState(null)
  const [highlightedBookingId, setHighlightedBookingId] = useState(null)
  const bookingRefs = useRef({})
  const highlightTimeout = useRef(null)

  useEffect(() => {
    const fetchBookings = async () => {
      setIsLoading(true)
      setError(null)
      try {
        const [bookingsRes, stationsRes] = await Promise.all([
          fetch(getApiEndpoint('/api/bookings')),
          fetch(getApiEndpoint('/api/stations'))
        ])

        if (!bookingsRes.ok) {
          throw new Error('Unable to load bookings.')
        }
        if (!stationsRes.ok) {
          throw new Error('Unable to load stations.')
        }

        const [bookingsPayload, stationsPayload] = await Promise.all([
          bookingsRes.json(),
          stationsRes.json()
        ])

        const stationsMap = stationsPayload.reduce((acc, station) => {
          acc[station.id] = station
          return acc
        }, {})

        const normalized = bookingsPayload.map((booking) => {
          const station = stationsMap[booking.stationId] || {}
          const start = booking.startTime ? new Date(booking.startTime) : null
          const end = booking.endTime ? new Date(booking.endTime) : null
          const status = mapStatus(booking.status)
          const durationHours = start && end ? (end - start) / (1000 * 60 * 60) : 0

          const locationParts = [station.city, station.country].filter(Boolean)

          return {
            id: booking.id,
            stationId: booking.stationId,
            stationName: station.displayName || 'Unknown Station',
            status,
            startTime: start,
            endTime: end,
            formattedDate: formatDate(start),
            formattedTime: formatTimeRange(start, end),
            vessel: booking.vesselId || '—',
            chargerType: booking.chargerType || '—',
            location: locationParts.join(', ') || '—',
            lat: typeof station.latitude === 'number' ? station.latitude : null,
            lng: typeof station.longitude === 'number' ? station.longitude : null,
            country: station.country || '',
            durationHours
          }
        })

        setBookings(normalized)
      } catch (fetchError) {
        setError(fetchError.message || 'Failed to load data.')
      } finally {
        setIsLoading(false)
      }
    }

    fetchBookings()

    return () => {
      if (highlightTimeout.current) {
        clearTimeout(highlightTimeout.current)
      }
    }
  }, [])

  const stats = useMemo(() => {
    if (!bookings.length) {
      return { upcoming: 0, total: 0, hours: 0 }
    }
    const now = new Date()
    const upcoming = bookings.filter(
      (booking) =>
        booking.startTime && booking.startTime > now && ['confirmed', 'pending'].includes(booking.status)
    ).length
    const totalHours = bookings.reduce((sum, booking) => sum + booking.durationHours, 0)

    return {
      upcoming,
      total: bookings.length,
      hours: Math.round(totalHours)
    }
  }, [bookings])

  const handleBookingFocus = (bookingId) => {
    if (!bookingId) return
    if (highlightTimeout.current) {
      clearTimeout(highlightTimeout.current)
    }
    setHighlightedBookingId(bookingId)
    const node = bookingRefs.current[bookingId]
    if (node) {
      node.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
    highlightTimeout.current = setTimeout(() => setHighlightedBookingId(null), 3000)
  }

  const renderStatValue = (value, suffix = '') => {
    if (isLoading) {
      return <Skeleton className="h-8 w-16" />
    }
    return (
      <div className="text-2xl font-bold">
        {value}
        {suffix}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">My Bookings</h1>
        <p className="mt-2 text-gray-600">Manage your charging station reservations</p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Upcoming Bookings</CardTitle>
            <Calendar className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {renderStatValue(stats.upcoming)}
            <p className="text-xs text-muted-foreground">Next 7 days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Sessions</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {renderStatValue(stats.total)}
            <p className="text-xs text-muted-foreground">All time</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Hours Charged</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {renderStatValue(stats.hours, 'h')}
            <p className="text-xs text-muted-foreground">Based on booking duration</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <Card className="h-full">
          <CardHeader>
            <CardTitle>All Bookings</CardTitle>
            <CardDescription>Your charging station reservations and history.</CardDescription>
          </CardHeader>
          <CardContent>
            {error && (
              <div className="mb-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                {error}
              </div>
            )}
            {isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((value) => (
                  <Skeleton key={value} className="h-24 w-full rounded-lg" />
                ))}
              </div>
            ) : bookings.length ? (
              <div className="space-y-4">
                {bookings.map((booking) => (
                  <div
                    key={booking.id}
                    ref={(node) => {
                      if (node) {
                        bookingRefs.current[booking.id] = node
                      } else {
                        delete bookingRefs.current[booking.id]
                      }
                    }}
                    className={`border rounded-lg p-4 transition-colors ${
                      highlightedBookingId === booking.id
                        ? 'ring-2 ring-primary ring-offset-2'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <h3 className="text-lg font-semibold">{booking.stationName}</h3>
                          <span
                            className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColors(
                              booking.status
                            )}`}
                          >
                            {booking.status.charAt(0).toUpperCase() + booking.status.slice(1)}
                          </span>
                        </div>
                        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            <span>{booking.formattedDate}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="h-4 w-4" />
                            <span>{booking.formattedTime}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <MapPin className="h-4 w-4" />
                            <span>{booking.location}</span>
                          </div>
                        </div>
                        <div className="flex flex-wrap items-center gap-4 text-sm">
                          <span className="text-gray-600">
                            Vessel: <span className="font-medium">{booking.vessel}</span>
                          </span>
                          <span className="text-gray-600">
                            Type: <span className="font-medium">{booking.chargerType}</span>
                          </span>
                        </div>
                      </div>
                      <div className="flex gap-2 text-sm">
                        {booking.status === 'confirmed' && (
                          <>
                            <button className="rounded-md border px-3 py-1 hover:bg-gray-50 transition-colors">
                              Modify
                            </button>
                            <button className="rounded-md border border-red-200 px-3 py-1 text-red-600 hover:bg-red-50 transition-colors">
                              Cancel
                            </button>
                          </>
                        )}
                        {booking.status === 'pending' && (
                          <button className="rounded-md border border-red-200 px-3 py-1 text-red-600 hover:bg-red-50 transition-colors">
                            Cancel
                          </button>
                        )}
                        {booking.status === 'completed' && (
                          <button className="rounded-md border px-3 py-1 hover:bg-gray-50 transition-colors">
                            View Details
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No bookings to display yet.</p>
            )}
          </CardContent>
        </Card>

        <PortMapCard bookings={bookings} isLoading={isLoading} onBookingFocus={handleBookingFocus} />
      </div>
    </div>
  )
}

export default MyBookings
