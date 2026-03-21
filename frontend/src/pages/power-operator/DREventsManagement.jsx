import { useEffect, useMemo, useState } from 'react'
import { MetricCard as DashboardMetricCard } from '@/components/ui/DashboardCards'
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
import { Activity, AlertCircle, CalendarPlus, Clock3, MapPin, RefreshCw, Send } from 'lucide-react'
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

const EVENT_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'created', label: 'Created' },
  { id: 'dispatched', label: 'Dispatched' },
  { id: 'active', label: 'Active' },
  { id: 'archived', label: 'Archived' },
]

const selectClassName =
  'h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

const toIsoString = (value) => {
  if (!value) return ''
  return new Date(value).toISOString()
}

const normalizeStatus = (status) => {
  if (!status) return 'Unknown'
  return String(status)
}

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

const WorkflowStep = ({ title, body }) => (
  <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{title}</div>
    <div className="mt-1 text-sm font-semibold leading-5 text-slate-900">{body}</div>
  </div>
)

const EventSummaryPanel = ({ event, stationLookup, loading }) => (
  <Card className="h-full">
    <CardHeader>
      <CardTitle className="mb-4 flex items-center gap-2 text-md font-light">
        <Clock3 className="h-4 w-4 text-muted-foreground" />
        Selected Event Summary
      </CardTitle>
      <CardDescription>
        Quick operational context for the selected event, or the most recent event in the current filter.
      </CardDescription>
    </CardHeader>
    <CardContent>
      {loading ? (
        <div className="space-y-3">
          <WorkflowStep title="Event" body="Loading..." />
          <WorkflowStep title="Status" body="Loading..." />
          <WorkflowStep title="Station" body="Loading..." />
          <WorkflowStep title="Window" body="Loading..." />
        </div>
      ) : !event ? (
        <div className="rounded-md border border-dashed border-muted px-4 py-10 text-center text-sm text-muted-foreground">
          No event is available in the current filter.
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-medium text-slate-900">{event.id}</p>
              <p className="text-xs text-muted-foreground">
                {stationLookup[event.stationId] || event.stationId}
              </p>
            </div>
            <Badge className={statusBadgeClass(event.status)}>
              {normalizeStatus(event.status)}
            </Badge>
          </div>
          <WorkflowStep
            title="Dispatch window"
            body={`${formatDateTime(event.startTime)} to ${formatDateTime(event.endTime)}`}
          />
          <WorkflowStep
            title="Energy target"
            body={`${Number(event.targetEnergyKwh || 0)} kWh @ $${Number(event.pricePerKwh || 0)}/kWh`}
          />
          <WorkflowStep
            title="Participants"
            body={`${Number(event.maxParticipants || 0)} max participants`}
          />
          <WorkflowStep
            title="Dispatch action"
            body={
              isDispatchableEvent(event.status)
                ? 'This event is ready for dispatch actions.'
                : 'Dispatch actions are unavailable for the current lifecycle state.'
            }
          />
        </div>
      )}
    </CardContent>
  </Card>
)

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
      <DialogContent className="max-w-5xl">
        <DialogHeader>
          <DialogTitle className="text-md font-light">DR Event Eligibility</DialogTitle>
          <DialogDescription>
            Current eligible vessels for {event.id}. This is the set that should be visible on the
            VO side after refresh.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5">
          <div className="grid gap-3 md:grid-cols-4">
            <WorkflowStep title="Status" body={normalizeStatus(event.status)} />
            <WorkflowStep title="Eligible now" body={String(eligibility?.eligibleCount ?? 0)} />
            <WorkflowStep
              title="Evaluated"
              body={String(eligibility?.totalVesselsEvaluated ?? 0)}
            />
            <WorkflowStep title="Window" body={formatDateTime(event.startTime)} />
          </div>

          {error ? (
            <Card className="border-destructive bg-destructive/5">
              <CardContent className="pt-4">
                <p className="text-sm text-destructive">{error}</p>
              </CardContent>
            </Card>
          ) : null}

          {isLoading ? (
            <div className="rounded-md border border-dashed border-muted px-4 py-8 text-center text-sm text-muted-foreground">
              Refreshing eligibility...
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-900">
                  Eligible Vessels ({eligibleVessels.length})
                </h3>
              </div>
              {eligibleVessels.length === 0 ? (
                <div className="rounded-md border border-dashed border-muted px-4 py-8 text-center text-sm text-muted-foreground">
                  No vessels are currently eligible for this event.
                </div>
              ) : (
                eligibleVessels.map((vessel) => (
                  <div
                    key={vessel.vesselId}
                    className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-medium text-slate-900">
                          {vessel.displayName || vessel.vesselId}
                        </p>
                        <p className="text-xs text-muted-foreground">{vessel.vesselId}</p>
                      </div>
                      <Badge className="bg-emerald-100 text-emerald-800">Eligible</Badge>
                    </div>
                    <div className="mt-4 grid gap-3 text-sm text-slate-600 sm:grid-cols-2 lg:grid-cols-3">
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
            <RefreshCw className="mr-2 h-4 w-4" />
            {isLoading ? 'Refreshing...' : 'Refresh Eligibility'}
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
  const [lastUpdatedAt, setLastUpdatedAt] = useState('')

  const authToken = localStorage.getItem('auth-token')
  const canViewDREvents = user?.type_name === 'POWER_OPERATOR'

  const stationLookup = useMemo(() => {
    return stations.reduce((accumulator, station) => {
      accumulator[station.id] = station.displayName || station.id
      return accumulator
    }, {})
  }, [stations])

  const managedEvents = useMemo(() => {
    return [...events].sort((left, right) => {
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

  const readyToDispatchCount = useMemo(
    () => managedEvents.filter((drEvent) => isDispatchableEvent(drEvent.status)).length,
    [managedEvents]
  )

  const uniqueStationCount = useMemo(
    () => new Set(managedEvents.map((drEvent) => drEvent.stationId).filter(Boolean)).size,
    [managedEvents]
  )

  const selectedOrLatestEvent = selectedEvent || filteredEvents.at(-1) || null

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

  const refreshData = async () => {
    try {
      await Promise.all([loadStations(), loadEvents()])
      setLastUpdatedAt(new Date().toISOString())
    } catch (loadError) {
      setError(loadError.message || 'Failed to load DR event data.')
    }
  }

  useEffect(() => {
    if (!canViewDREvents) {
      return
    }

    refreshData()
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
      setLastUpdatedAt(new Date().toISOString())
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
      setLastUpdatedAt(new Date().toISOString())
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
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-4 h-12 w-12 text-red-500" />
          <h3 className="mb-2 text-lg font-semibold text-gray-900">Access Denied</h3>
          <p className="text-gray-600">Only power operator accounts can access DR events.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
        <div className="mb-2">
          <h1 className="text-3xl font-bold text-gray-900">DR Events</h1>
          <p className="mt-2 text-gray-600">
            Last updated:{' '}
            <span className="text-sm text-muted-foreground">
              {lastUpdatedAt ? new Date(lastUpdatedAt).toLocaleString() : '—'}
            </span>
          </p>
        </div>
        <Button type="button" variant="outline" onClick={refreshData} disabled={isLoading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {error ? (
        <Card className="border-destructive bg-destructive/5">
          <CardContent className="pt-4">
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      ) : null}
      {successMessage ? (
        <Card className="border-emerald-200 bg-emerald-50/50">
          <CardContent className="pt-4">
            <p className="text-sm text-emerald-800">{successMessage}</p>
          </CardContent>
        </Card>
      ) : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <DashboardMetricCard
          title="Total events"
          value={String(eventCounts.all)}
          helper="Across all lifecycle stages"
          icon={CalendarPlus}
          loading={isLoading}
          valueClassName="text-3xl font-medium"
        />
        <DashboardMetricCard
          title="Ready to dispatch"
          value={String(readyToDispatchCount)}
          helper="Created or dispatched events awaiting action"
          icon={Send}
          loading={isLoading}
          valueClassName="text-3xl font-medium"
        />
        <DashboardMetricCard
          title="Active now"
          value={String(eventCounts.active)}
          helper="Currently executing DR events"
          icon={Activity}
          loading={isLoading}
          valueClassName="text-3xl font-medium"
        />
        <DashboardMetricCard
          title="Stations involved"
          value={String(uniqueStationCount)}
          helper="Distinct stations across tracked events"
          icon={MapPin}
          loading={isLoading}
          valueClassName="text-3xl font-medium"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
        <Card>
          <CardHeader>
            <CardTitle className="mb-4 flex items-center gap-2 text-md font-light">
              <CalendarPlus className="h-4 w-4 text-muted-foreground" />
              Create DR Event
            </CardTitle>
            <CardDescription>
              Fields match the DREvent object model and backend API contract.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="grid grid-cols-1 gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
              <div className="space-y-2">
                <Label htmlFor="stationId">Station</Label>
                <select
                  id="stationId"
                  className={selectClassName}
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
                  rows={5}
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

        <EventSummaryPanel
          event={selectedOrLatestEvent}
          stationLookup={stationLookup}
          loading={isLoading}
        />
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <CardTitle className="text-md font-light">Existing DR Events</CardTitle>
            <CardDescription>
              Create events, dispatch contract offers, and monitor lifecycle status from one place.
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
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
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="rounded-md border border-dashed border-muted px-4 py-10 text-center text-sm text-muted-foreground">
              Loading DR events...
            </div>
          ) : filteredEvents.length === 0 ? (
            <div className="rounded-md border border-dashed border-muted px-4 py-10 text-center text-sm text-muted-foreground">
              {eventFilter === 'all'
                ? 'No DR events found.'
                : `No ${eventFilter} DR events found.`}
            </div>
          ) : (
            <div className="space-y-3">
              {filteredEvents.map((drEvent) => (
                <button
                  key={drEvent.id}
                  type="button"
                  className="group w-full rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:border-slate-300 hover:bg-slate-50/80"
                  onClick={() => handleOpenEvent(drEvent)}
                >
                  <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                    <div className="space-y-1">
                      <p className="font-medium text-slate-900">{drEvent.id}</p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(drEvent.startTime)} to {formatDateTime(drEvent.endTime)}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className={statusBadgeClass(drEvent.status)}>
                        {normalizeStatus(drEvent.status)}
                      </Badge>
                      {isDispatchableEvent(drEvent.status) ? (
                        <Button
                          type="button"
                          size="sm"
                          onClick={(event) => {
                            event.stopPropagation()
                            handleDispatch(drEvent.id)
                          }}
                          disabled={dispatchingEventId === drEvent.id}
                        >
                          <Send className="mr-2 h-4 w-4" />
                          {dispatchingEventId === drEvent.id
                            ? 'Dispatching...'
                            : String(drEvent.status).toLowerCase() === 'created'
                              ? 'Dispatch'
                              : 'Refresh Dispatch'}
                        </Button>
                      ) : null}
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <WorkflowStep
                      title="Station"
                      body={stationLookup[drEvent.stationId] || drEvent.stationId}
                    />
                    <WorkflowStep
                      title="Energy / price"
                      body={`${Number(drEvent.targetEnergyKwh)} kWh @ $${Number(drEvent.pricePerKwh)}/kWh`}
                    />
                    <WorkflowStep
                      title="Participants"
                      body={`${Number(drEvent.maxParticipants || 0)} max participants`}
                    />
                  </div>
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
