import { useEffect, useMemo, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  FileText,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  RefreshCw,
  Zap,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { getApiEndpoint } from '@/config/api'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STATUS_FILTERS = ['all', 'pending', 'active', 'completed', 'cancelled']

const statusBadgeClass = (status) => {
  switch (status) {
    case 'pending':
      return 'bg-yellow-100 text-yellow-800'
    case 'active':
      return 'bg-emerald-100 text-emerald-800'
    case 'completed':
      return 'bg-blue-100 text-blue-800'
    case 'cancelled':
      return 'bg-gray-100 text-gray-800'
    case 'failed':
      return 'bg-red-100 text-red-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const StatusIcon = ({ status }) => {
  switch (status) {
    case 'pending':
      return <Clock className="h-3 w-3" />
    case 'active':
      return <CheckCircle className="h-3 w-3" />
    case 'completed':
      return <CheckCircle className="h-3 w-3" />
    case 'cancelled':
      return <XCircle className="h-3 w-3" />
    case 'failed':
      return <AlertCircle className="h-3 w-3" />
    default:
      return <FileText className="h-3 w-3" />
  }
}

const formatDateTime = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleString()
}

const formatCurrency = (value) =>
  typeof value === 'number' ? `$${value.toFixed(2)}` : '—'

const formatPendingEnergy = (contract) => {
  if (contract.status === 'pending') {
    return 'Contribution set on acceptance'
  }
  return `${contract.energyAmount} kWh`
}

// ---------------------------------------------------------------------------
// Contract detail modal
// ---------------------------------------------------------------------------

const ContractDetailModal = ({
  contract,
  acceptanceForm,
  onAcceptanceFormChange,
  onClose,
  onAccept,
  onDecline,
  isActioning,
}) => {
  if (!contract) return null

  const isPending = contract.status === 'pending'

  return (
    <Dialog open onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Contract Details
          </DialogTitle>
          <DialogDescription>
            Review the full terms before accepting or declining.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-500">Status</span>
            <Badge className={`${statusBadgeClass(contract.status)} flex items-center gap-1`}>
              <StatusIcon status={contract.status} />
              <span className="capitalize">{contract.status}</span>
            </Badge>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-500">Vessel</span>
            <span className="font-medium">{contract.vesselName}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-500">Energy Amount</span>
            <span className="font-medium">{formatPendingEnergy(contract)}</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-500">Committed Power</span>
            <span className="font-medium">
              {contract.committedPowerKw ? `${contract.committedPowerKw} kW` : 'Not submitted'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-500">Rate</span>
            <span className="font-medium">${contract.pricePerKwh}/kWh</span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-500">Total Value</span>
            <span className="font-bold text-emerald-700">
              {contract.status === 'pending'
                ? 'Calculated on acceptance'
                : formatCurrency(contract.totalValue)}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-500">Window</span>
            <span className="font-medium text-right">
              {formatDateTime(contract.startTime)}
              <br />— {formatDateTime(contract.endTime)}
            </span>
          </div>

          <div>
            <p className="text-gray-500 mb-1">Terms</p>
            <p className="rounded-md border bg-gray-50 p-3 text-gray-700 text-xs leading-relaxed">
              {contract.terms || '—'}
            </p>
          </div>

          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>Contract ID: {contract.id}</span>
            <span>Issued: {formatDateTime(contract.createdAt)}</span>
          </div>

          {isPending && (
            <div className="space-y-3 rounded-md border bg-slate-50 p-4">
              <div className="space-y-2">
                <Label htmlFor="committedPowerKw">Committed discharge power (kW)</Label>
                <Input
                  id="committedPowerKw"
                  type="number"
                  min="0.1"
                  step="0.1"
                  value={acceptanceForm.committedPowerKw}
                  onChange={(event) => onAcceptanceFormChange('committedPowerKw', event.target.value)}
                  placeholder="Enter the power you can commit"
                  disabled={isActioning}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="operatorNotes">Operator notes</Label>
                <Textarea
                  id="operatorNotes"
                  rows={3}
                  value={acceptanceForm.operatorNotes}
                  onChange={(event) => onAcceptanceFormChange('operatorNotes', event.target.value)}
                  placeholder="Optional notes for this dispatch"
                  disabled={isActioning}
                />
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="flex gap-2">
          <Button variant="outline" onClick={onClose} disabled={isActioning}>
            Close
          </Button>
          {isPending && (
            <>
              <Button
                variant="outline"
                className="text-red-600 border-red-300 hover:bg-red-50"
                onClick={() => onDecline(contract.id)}
                disabled={isActioning}
              >
                <XCircle className="h-4 w-4 mr-1" />
                {isActioning ? 'Declining…' : 'Decline'}
              </Button>
              <Button
                className="bg-emerald-600 hover:bg-emerald-700 text-white"
                onClick={() => onAccept(contract.id)}
                disabled={isActioning}
              >
                <CheckCircle className="h-4 w-4 mr-1" />
                {isActioning ? 'Accepting…' : 'Accept'}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

const MyContracts = () => {
  const { user } = useAuth()
  const [contracts, setContracts] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [selectedContract, setSelectedContract] = useState(null)
  const [isActioning, setIsActioning] = useState(false)
  const [actionMessage, setActionMessage] = useState('')
  const [acceptanceForm, setAcceptanceForm] = useState({
    committedPowerKw: '',
    operatorNotes: '',
  })

  const authToken = localStorage.getItem('auth-token')
  const canViewContracts = user?.type_name === 'VESSEL_OPERATOR'

  const filteredContracts = useMemo(() => {
    if (statusFilter === 'all') return contracts
    return contracts.filter((c) => c.status === statusFilter)
  }, [contracts, statusFilter])

  const pendingCount = useMemo(
    () => contracts.filter((c) => c.status === 'pending').length,
    [contracts]
  )

  // ---------------------------------------------------------------------------
  // API calls
  // ---------------------------------------------------------------------------

  const loadContracts = async () => {
    if (!authToken) {
      setError('Missing authentication token.')
      return
    }
    setIsLoading(true)
    setError('')
    try {
      const response = await fetch(getApiEndpoint('/api/contracts/my-contracts'), {
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || 'Failed to load contracts')
      }
      const data = await response.json()
      setContracts(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || 'Unable to load contracts.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAccept = async (contractId) => {
    if (!String(acceptanceForm.committedPowerKw || '').trim()) {
      setError('Committed discharge power is required before accepting a contract.')
      return
    }

    setIsActioning(true)
    setError('')
    setActionMessage('')
    try {
      const response = await fetch(getApiEndpoint(`/api/contracts/${contractId}/accept`), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${authToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          committedPowerKw: acceptanceForm.committedPowerKw,
          operatorNotes: acceptanceForm.operatorNotes,
        }),
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || 'Failed to accept contract')
      }
      const data = await response.json()
      setContracts((prev) =>
        prev.map((c) => (c.id === contractId ? data.contract : c))
      )
      setSelectedContract(data.contract)
      setAcceptanceForm({
        committedPowerKw: String(data.contract.committedPowerKw || ''),
        operatorNotes: data.contract.operatorNotes || '',
      })
      setActionMessage('Contract accepted successfully.')
    } catch (err) {
      setError(err.message || 'Failed to accept contract.')
    } finally {
      setIsActioning(false)
    }
  }

  const handleDecline = async (contractId) => {
    setIsActioning(true)
    setError('')
    setActionMessage('')
    try {
      const response = await fetch(getApiEndpoint(`/api/contracts/${contractId}/decline`), {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}` },
      })
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}))
        throw new Error(payload.error || 'Failed to decline contract')
      }
      const data = await response.json()
      setContracts((prev) =>
        prev.map((c) => (c.id === contractId ? data.contract : c))
      )
      setSelectedContract(null)
      setAcceptanceForm({
        committedPowerKw: '',
        operatorNotes: '',
      })
      setActionMessage('Contract declined.')
    } catch (err) {
      setError(err.message || 'Failed to decline contract.')
    } finally {
      setIsActioning(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Effects
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (!canViewContracts) return
    loadContracts()
  }, [canViewContracts, user])

  useEffect(() => {
    if (!selectedContract) {
      setAcceptanceForm({
        committedPowerKw: '',
        operatorNotes: '',
      })
      return
    }
    setAcceptanceForm({
      committedPowerKw: selectedContract.committedPowerKw
        ? String(selectedContract.committedPowerKw)
        : '',
      operatorNotes: selectedContract.operatorNotes || '',
    })
  }, [selectedContract])

  // ---------------------------------------------------------------------------
  // Access guard
  // ---------------------------------------------------------------------------

  if (!canViewContracts) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Access Denied</h3>
          <p className="text-gray-600">Only vessel operator accounts can view contracts.</p>
        </div>
      </div>
    )
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">My Contracts</h1>
          <p className="text-gray-600 mt-1">
            Review dispatched DR contract offers assigned to your vessels and submit your commitment.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={loadContracts} disabled={isLoading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Notifications */}
      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
      {actionMessage && (
        <div className="rounded-md border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          {actionMessage}
        </div>
      )}

      {/* Pending inbox callout */}
      {pendingCount > 0 && (
        <div className="rounded-md border border-yellow-200 bg-yellow-50 p-4 flex items-center gap-3">
          <Clock className="h-5 w-5 text-yellow-600 shrink-0" />
          <p className="text-sm text-yellow-800">
            You have <span className="font-semibold">{pendingCount}</span> pending contract
            {pendingCount !== 1 ? 's' : ''} awaiting your response.
          </p>
        </div>
      )}

      {/* Status filter tabs */}
      <div className="flex flex-wrap gap-2">
        {STATUS_FILTERS.map((f) => (
          <Button
            key={f}
            variant={statusFilter === f ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter(f)}
            className="capitalize"
          >
            {f}
          </Button>
        ))}
      </div>

      {/* Contract list */}
      {isLoading ? (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
          <p className="mt-3 text-gray-500 text-sm">Loading contracts…</p>
        </div>
      ) : filteredContracts.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-1">No Contracts Found</h3>
            <p className="text-gray-500 text-sm">
              {statusFilter !== 'all'
                ? `No ${statusFilter} contracts to display.`
                : 'No contracts have been assigned to your vessels yet.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filteredContracts.map((contract) => (
            <Card
              key={contract.id}
              className="hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => setSelectedContract(contract)}
            >
              <CardContent className="pt-5 pb-4">
                <div className="flex items-start justify-between gap-4">
                  {/* Left: vessel + timing */}
                  <div className="flex-1 min-w-0 space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-semibold text-gray-900">{contract.vesselName}</span>
                      <Badge
                        className={`${statusBadgeClass(contract.status)} flex items-center gap-1 text-xs`}
                      >
                        <StatusIcon status={contract.status} />
                        <span className="capitalize">{contract.status}</span>
                      </Badge>
                    </div>
                    <p className="text-xs text-gray-500 truncate">ID: {contract.id}</p>
                    <p className="text-xs text-gray-500">
                      {formatDateTime(contract.startTime)} — {formatDateTime(contract.endTime)}
                    </p>
                  </div>

                  {/* Right: financials + actions */}
                  <div className="text-right shrink-0 space-y-2">
                    <div>
                      <p className="text-lg font-bold text-emerald-700">
                        {contract.status === 'pending'
                          ? 'Open offer'
                          : formatCurrency(contract.totalValue)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {contract.status === 'pending'
                          ? `Commit your own discharge rate @ $${contract.pricePerKwh}/kWh`
                          : `${contract.energyAmount} kWh @ $${contract.pricePerKwh}/kWh`}
                      </p>
                    </div>

                    {contract.status === 'pending' && (
                      <div className="flex gap-2 justify-end" onClick={(e) => e.stopPropagation()}>
                        <Button
                          size="sm"
                          onClick={() => setSelectedContract(contract)}
                        >
                          <Zap className="h-3.5 w-3.5 mr-1" />
                          Review Offer
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Detail modal */}
      {selectedContract && (
        <ContractDetailModal
          contract={selectedContract}
          acceptanceForm={acceptanceForm}
          onAcceptanceFormChange={(field, value) =>
            setAcceptanceForm((current) => ({ ...current, [field]: value }))
          }
          onClose={() => setSelectedContract(null)}
          onAccept={handleAccept}
          onDecline={handleDecline}
          isActioning={isActioning}
        />
      )}
    </div>
  )
}

export default MyContracts
