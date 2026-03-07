import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { CalendarPlus, RefreshCw, AlertCircle, Send } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { getApiEndpoint } from '@/config/api'

const INITIAL_FORM = {
  stationId: '',
  pricePerKwh: '',
  targetEnergyKwh: '',
  maxParticipants: '',
  startTime: '',
  endTime: '',
  details: '{}',
}

const toIsoString = (value) => {
  if (!value) return ''
  return new Date(value).toISOString()
}

const normalizeStatus = (status) => {
  if (!status) return 'Unknown'
  return String(status)
}

const EVENT_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'created', label: 'Created' },
  { id: 'dispatched', label: 'Dispatched' },
  { id: 'active', label: 'Active' },
  { id: 'archived', label: 'Archived' },
]

const getEventCategory = (status) => {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'created') return 'created'
  if (['dispatched', 'accepted', 'committed'].includes(normalized)) return 'dispatched'
  if (normalized === 'active') return 'active'
  if (['completed', 'settled', 'archived', 'cancelled'].includes(normalized)) return 'archived'
  return 'all'
}

const statusBadgeClass = (status) => {
  const normalized = String(status || '').toLowerCase()
  if (normalized === 'created') return 'bg-blue-100 text-blue-800'
  if (normalized === 'dispatched') return 'bg-amber-100 text-amber-800'
  if (normalized === 'accepted') return 'bg-indigo-100 text-indigo-800'
  if (normalized === 'committed') return 'bg-violet-100 text-violet-800'
  if (normalized === 'active') return 'bg-emerald-100 text-emerald-800'
  if (normalized === 'completed') return 'bg-slate-100 text-slate-800'
  if (normalized === 'cancelled') return 'bg-rose-100 text-rose-800'
  return 'bg-gray-100 text-gray-800'
}

const isDispatchableEvent = (status) => {
  const normalized = String(status || '').toLowerCase()
  return normalized === 'created' || normalized === 'dispatched'
}

const formatDateTime = (value) => {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

const formatNumber = (value, digits = 1) => {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—'
  return value.toFixed(digits)
}

const EventEligibilityDialog = ({
  event,
  isOpen,
  onClose,
  onRefresh,
  isLoading,
  eligibility,
  error,
}) => {
  if (!event) return null

  const vessels = Array.isArray(eligibility?.vessels) ? eligibility.vessels : []
  const eligibleVessels = vessels.filter((vessel) => vessel.eligible)

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>DR Event Eligibility</DialogTitle>
          <DialogDescription>
            Current eligible vessels for {event.id}. This is the set that should be visible on the
            VO side after refresh.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-3 md:grid-cols-4">
            <div className="rounded-md border bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Status</p>
              <p className="mt-1 font-semibold text-gray-900">{normalizeStatus(event.status)}</p>
            </div>
            <div className="rounded-md border bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Eligible Now</p>
              <p className="mt-1 font-semibold text-gray-900">{eligibility?.eligibleCount ?? 0}</p>
            </div>
            <div className="rounded-md border bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Evaluated</p>
              <p className="mt-1 font-semibold text-gray-900">
                {eligibility?.totalVesselsEvaluated ?? 0}
              </p>
            </div>
            <div className="rounded-md border bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-gray-500">Window</p>
              <p className="mt-1 text-sm font-semibold text-gray-900">
                {formatDateTime(event.startTime)}
              </p>
              <p className="text-xs text-gray-500">{formatDateTime(event.endTime)}</p>
            </div>
          </div>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {isLoading ? (
            <p className="text-sm text-gray-500">Refreshing eligibility…</p>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">
                  Eligible Vessels ({eligibleVessels.length})
                </h3>
              </div>
              {eligibleVessels.length === 0 ? (
                <p className="rounded-md border p-3 text-sm text-gray-500">
                  No vessels are currently eligible for this event.
                </p>
              ) : (
                eligibleVessels.map((vessel) => (
                  <div key={vessel.vesselId} className="rounded-md border p-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium text-gray-900">
                          {vessel.displayName || vessel.vesselId}
                        </p>
                        <p className="text-xs text-gray-500">{vessel.vesselId}</p>
                      </div>
                      <Badge className="bg-emerald-100 text-emerald-800">Eligible</Badge>
                    </div>
                    <div className="mt-3 grid gap-2 text-sm text-gray-600 sm:grid-cols-2">
                      <p>Current SoC: {formatNumber(vessel.currentSoc)}%</p>
                      <p>Forecasted SoC: {formatNumber(vessel.forecastedSoc)}%</p>
                      <p>Available battery: {formatNumber(vessel.availableBatteryKwh)} kWh</p>
                      <p>Required energy: {formatNumber(vessel.requiredEnergyPerVesselKwh)} kWh</p>
                      <p>Distance: {formatNumber(vessel.distanceKm)} km</p>
                      <p>Charger type: {vessel.chargerType || '—'}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button type="button" onClick={onRefresh} disabled={isLoading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            {isLoading ? 'Refreshing…' : 'Refresh Eligibility'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

const DREventsManagement = () => {
  const { user } = useAuth()
  const [events, setEvents] = useState([])
  const [stations, setStations] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [dispatchingEventId, setDispatchingEventId] = useState('')
  const [selectedEvent, setSelectedEvent] = useState(null)
  const [eligibilitySnapshot, setEligibilitySnapshot] = useState(null)
  const [isLoadingEligibility, setIsLoadingEligibility] = useState(false)
  const [eligibilityError, setEligibilityError] = useState('')
  const [error, setError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [eventFilter, setEventFilter] = useState('all')
  const [formData, setFormData] = useState(INITIAL_FORM)

  const authToken = localStorage.getItem('auth-token')
  const canViewDREvents = user?.type_name === 'POWER_OPERATOR'

  const stationLookup = useMemo(() => {
    return stations.reduce((accumulator, station) => {
      accumulator[station.id] = station.displayName || station.id
      return accumulator
    }, {})
  }, [stations])

  const managedEvents = useMemo(() => {
    return [...events]
      .sort((left, right) => {
        const leftTime = new Date(left.startTime || 0).getTime()
        const rightTime = new Date(right.startTime || 0).getTime()
        return leftTime - rightTime
      })
  }, [events])

  const filteredEvents = useMemo(() => {
    if (eventFilter === 'all') {
      return managedEvents
    }
    return managedEvents.filter((drEvent) => getEventCategory(drEvent.status) === eventFilter)
  }, [eventFilter, managedEvents])

  const eventCounts = useMemo(() => {
    return managedEvents.reduce(
      (counts, drEvent) => {
        const category = getEventCategory(drEvent.status)
        counts.all += 1
        if (counts[category] !== undefined) {
          counts[category] += 1
        }
        return counts
      },
      {
        all: 0,
        created: 0,
        dispatched: 0,
        active: 0,
        archived: 0,
      }
    )
  }, [managedEvents])

  const loadStations = async () => {
    const response = await fetch(getApiEndpoint('/api/stations'))
    if (!response.ok) {
      throw new Error('Failed to load stations')
    }
    const payload = await response.json()
    setStations(Array.isArray(payload) ? payload : [])
  }

  const loadEvents = async () => {
    if (!authToken) {
      setError('Missing authentication token.')
      return
    }

    setIsLoading(true)
    setError('')
    try {
      const response = await fetch(getApiEndpoint('/api/drevents'), {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      if (!response.ok) {
        const responsePayload = await response.json().catch(() => ({}))
        throw new Error(
          responsePayload.details || responsePayload.error || 'Failed to load DR events'
        )
      }

      const payload = await response.json()
      setEvents(Array.isArray(payload) ? payload : [])
    } catch (loadError) {
      setError(loadError.message || 'Unable to load DR events.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (!canViewDREvents) {
      return
    }

    const fetchData = async () => {
      try {
        await Promise.all([loadStations(), loadEvents()])
      } catch (loadError) {
        setError(loadError.message || 'Failed to load DR event data.')
      }
    }

    fetchData()
  }, [canViewDREvents, user])

  const handleFieldChange = (field, value) => {
    setFormData((previous) => ({ ...previous, [field]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSuccessMessage('')

    if (!authToken) {
      setError('Missing authentication token.')
      return
    }

    let parsedDetails = {}
    try {
      parsedDetails = formData.details ? JSON.parse(formData.details) : {}
    } catch {
      setError('Details must be valid JSON.')
      return
    }

    const payload = {
      stationId: formData.stationId,
      pricePerKwh: Number(formData.pricePerKwh),
      targetEnergyKwh: Number(formData.targetEnergyKwh),
      maxParticipants: Number(formData.maxParticipants),
      startTime: toIsoString(formData.startTime),
      endTime: toIsoString(formData.endTime),
      details: parsedDetails,
    }

    setIsSubmitting(true)
    try {
      const response = await fetch(getApiEndpoint('/api/drevents'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const responsePayload = await response.json().catch(() => ({}))
        throw new Error(responsePayload.error || 'Failed to create DR event')
      }

      setFormData(INITIAL_FORM)
      setSuccessMessage('DR event created successfully. Dispatch it from the event list when ready.')
      await loadEvents()
    } catch (submitError) {
      setError(submitError.message || 'Failed to create DR event.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDispatch = async (eventId) => {
    if (!authToken) {
      setError('Missing authentication token.')
      return
    }

    setDispatchingEventId(eventId)
    setError('')
    setSuccessMessage('')

    try {
      const response = await fetch(getApiEndpoint(`/api/drevents/${eventId}/dispatch`), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      })

      const payload = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(payload.error || 'Failed to dispatch DR event')
      }

      const createdCount = Number(payload.contractsCreated || 0)
      const skippedCount = Number(payload.contractsSkipped || 0)
      const eligibleCount = Number(payload.eligibleVessels || 0)
      setSuccessMessage(
        `Dispatched ${eventId}: ${createdCount} contract offer${createdCount === 1 ? '' : 's'} created, ` +
          `${skippedCount} skipped, ${eligibleCount} eligible vessel${eligibleCount === 1 ? '' : 's'} evaluated.`
      )
      await loadEvents()
    } catch (dispatchError) {
      setError(dispatchError.message || 'Failed to dispatch DR event.')
    } finally {
      setDispatchingEventId('')
    }
  }

  const loadEligibilitySnapshot = async (eventId) => {
    if (!authToken) {
      setEligibilityError('Missing authentication token.')
      return
    }

    setIsLoadingEligibility(true)
    setEligibilityError('')
    try {
      const response = await fetch(
        getApiEndpoint(`/api/drevents/${eventId}/eligibility?includeIneligible=true`),
        {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
        }
      )

      const payload = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(payload.error || 'Failed to load event eligibility')
      }

      setEligibilitySnapshot(payload)
    } catch (loadError) {
      setEligibilitySnapshot(null)
      setEligibilityError(loadError.message || 'Failed to load event eligibility.')
    } finally {
      setIsLoadingEligibility(false)
    }
  }

  const handleOpenEvent = async (event) => {
    setSelectedEvent(event)
    setEligibilitySnapshot(null)
    await loadEligibilitySnapshot(event.id)
  }

  if (!canViewDREvents) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Access Denied</h3>
          <p className="text-gray-600">Only power operator accounts can access DR events.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">DR Event Creation</h1>
          <p className="text-gray-600 mt-2">Create demand-response events for vessel dispatch</p>
        </div>
        <Button type="button" variant="outline" onClick={loadEvents} disabled={isLoading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}
      {successMessage && (
        <div className="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          {successMessage}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarPlus className="h-5 w-5" />
            Create DR Event
          </CardTitle>
          <CardDescription>Fields match the DREvent object model and backend API contract.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid grid-cols-1 md:grid-cols-2 gap-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="stationId">Station</Label>
              <select
                id="stationId"
                className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm"
                value={formData.stationId}
                onChange={(event) => handleFieldChange('stationId', event.target.value)}
                required
              >
                <option value="">Select station</option>
                {stations.map((station) => (
                  <option key={station.id} value={station.id}>
                    {station.displayName || station.id}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="maxParticipants">Max Participants</Label>
              <Input
                id="maxParticipants"
                type="number"
                min="1"
                step="1"
                value={formData.maxParticipants}
                onChange={(event) => handleFieldChange('maxParticipants', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="pricePerKwh">Price per kWh</Label>
              <Input
                id="pricePerKwh"
                type="number"
                min="0"
                step="0.01"
                value={formData.pricePerKwh}
                onChange={(event) => handleFieldChange('pricePerKwh', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="targetEnergyKwh">Target Energy (kWh)</Label>
              <Input
                id="targetEnergyKwh"
                type="number"
                min="0"
                step="0.1"
                value={formData.targetEnergyKwh}
                onChange={(event) => handleFieldChange('targetEnergyKwh', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="startTime">Start Time</Label>
              <Input
                id="startTime"
                type="datetime-local"
                value={formData.startTime}
                onChange={(event) => handleFieldChange('startTime', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="endTime">End Time</Label>
              <Input
                id="endTime"
                type="datetime-local"
                value={formData.endTime}
                onChange={(event) => handleFieldChange('endTime', event.target.value)}
                required
              />
            </div>

            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="details">Details (JSON)</Label>
              <Textarea
                id="details"
                value={formData.details}
                onChange={(event) => handleFieldChange('details', event.target.value)}
                rows={4}
              />
            </div>

            <div className="md:col-span-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Creating...' : 'Create DR Event'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Existing DR Events</CardTitle>
          <CardDescription>
            Create events, dispatch contract offers, and monitor lifecycle status from one place.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2 mb-4">
            {EVENT_FILTERS.map((filter) => (
              <Button
                key={filter.id}
                type="button"
                variant={eventFilter === filter.id ? 'default' : 'outline'}
                size="sm"
                onClick={() => setEventFilter(filter.id)}
              >
                {filter.label} ({eventCounts[filter.id] ?? 0})
              </Button>
            ))}
          </div>

          {isLoading ? (
            <p className="text-sm text-gray-500">Loading DR events...</p>
          ) : filteredEvents.length === 0 ? (
            <p className="text-sm text-gray-500">
              {eventFilter === 'all'
                ? 'No DR events found.'
                : `No ${eventFilter} DR events found.`}
            </p>
          ) : (
            <div className="space-y-3">
              {filteredEvents.map((drEvent) => (
                <button
                  key={drEvent.id}
                  type="button"
                  className="w-full rounded-md border p-3 text-left transition-colors hover:bg-slate-50"
                  onClick={() => handleOpenEvent(drEvent)}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="space-y-1">
                      <p className="text-sm font-medium text-gray-900">{drEvent.id}</p>
                      <p className="text-xs text-gray-500">
                        {formatDateTime(drEvent.startTime)} - {formatDateTime(drEvent.endTime)}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge className={statusBadgeClass(drEvent.status)}>
                        {normalizeStatus(drEvent.status)}
                      </Badge>
                      {isDispatchableEvent(drEvent.status) && (
                        <Button
                          type="button"
                          size="sm"
                          onClick={(event) => {
                            event.stopPropagation()
                            handleDispatch(drEvent.id)
                          }}
                          disabled={dispatchingEventId === drEvent.id}
                        >
                          <Send className="h-4 w-4 mr-2" />
                          {dispatchingEventId === drEvent.id
                            ? 'Dispatching...'
                            : String(drEvent.status).toLowerCase() === 'created'
                              ? 'Dispatch'
                              : 'Refresh Dispatch'}
                        </Button>
                      )}
                    </div>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    Station: {stationLookup[drEvent.stationId] || drEvent.stationId}
                  </p>
                  <p className="text-sm text-gray-600">
                    {Number(drEvent.targetEnergyKwh)} kWh @ ${Number(drEvent.pricePerKwh)}/kWh
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Max participants: {Number(drEvent.maxParticipants || 0)}
                  </p>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <EventEligibilityDialog
        event={selectedEvent}
        isOpen={Boolean(selectedEvent)}
        onClose={() => {
          setSelectedEvent(null)
          setEligibilitySnapshot(null)
          setEligibilityError('')
        }}
        onRefresh={() => selectedEvent && loadEligibilitySnapshot(selectedEvent.id)}
        isLoading={isLoadingEligibility}
        eligibility={eligibilitySnapshot}
        error={eligibilityError}
      />
    </div>
  )
}

export default DREventsManagement
