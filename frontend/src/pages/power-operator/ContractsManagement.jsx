import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription, 
  DialogFooter, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger 
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { Search, Plus, FileText, X, CheckCircle, Clock, AlertCircle } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'

const ContractsManagement = () => {
  const { user } = useAuth()
  const [contracts, setContracts] = useState([])
  const [filteredContracts, setFilteredContracts] = useState([])
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [vessels, setVessels] = useState([])
  
  // Form state for creating new contract
  const [newContract, setNewContract] = useState({
    vesselId: '',
    energyAmount: '',
    pricePerKwh: '',
    startTime: '',
    endTime: '',
    terms: ''
  })

  // Mock contracts data - replace with API call
  const mockContracts = [
    {
      id: 'contract-001',
      vesselId: 'vessel-001',
      vesselName: 'Sea Breeze',
      energyAmount: 150,
      pricePerKwh: 0.15,
      totalValue: 22.50,
      startTime: '2025-10-27T09:00:00',
      endTime: '2025-10-27T17:00:00',
      status: 'active',
      createdAt: '2025-10-26T10:00:00',
      terms: 'Standard vessel-to-grid energy transaction terms'
    },
    {
      id: 'contract-002',
      vesselId: 'vessel-002',
      vesselName: 'Ocean Explorer',
      energyAmount: 200,
      pricePerKwh: 0.18,
      totalValue: 36.00,
      startTime: '2025-10-28T08:00:00',
      endTime: '2025-10-28T18:00:00',
      status: 'pending',
      createdAt: '2025-10-26T14:30:00',
      terms: 'Peak hour energy transaction with premium rates'
    },
    {
      id: 'contract-003',
      vesselId: 'vessel-003',
      vesselName: 'Wave Runner',
      energyAmount: 75,
      pricePerKwh: 0.12,
      totalValue: 9.00,
      startTime: '2025-10-25T14:00:00',
      endTime: '2025-10-25T20:00:00',
      status: 'completed',
      createdAt: '2025-10-25T08:00:00',
      terms: 'Off-peak energy transaction'
    },
    {
      id: 'contract-004',
      vesselId: 'vessel-004',
      vesselName: 'Harbor Master',
      energyAmount: 300,
      pricePerKwh: 0.20,
      totalValue: 60.00,
      startTime: '2025-10-26T06:00:00',
      endTime: '2025-10-26T12:00:00',
      status: 'failed',
      createdAt: '2025-10-25T18:00:00',
      terms: 'High-capacity energy transfer agreement'
    }
  ]

  // Mock vessels data - replace with API call
  const mockVessels = [
    { id: 'vessel-001', name: 'Sea Breeze', owner: 'John Smith' },
    { id: 'vessel-002', name: 'Ocean Explorer', owner: 'Marina Corp' },
    { id: 'vessel-003', name: 'Wave Runner', owner: 'Coast Guard' },
    { id: 'vessel-004', name: 'Harbor Master', owner: 'Port Authority' },
    { id: 'vessel-005', name: 'Blue Horizon', owner: 'Private Owner' }
  ]

  useEffect(() => {
    // Check if user has admin role
    if (user?.role_name !== 'ADMIN') {
      // This should be handled by route protection, but double-check here
      return
    }

    // Load contracts and vessels data
    loadContracts()
    loadVessels()
  }, [user])

  useEffect(() => {
    // Filter contracts based on search and status
    let filtered = contracts.filter(contract => {
      const matchesSearch = contract.vesselName.toLowerCase().includes(searchQuery.toLowerCase()) ||
                           contract.id.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesStatus = statusFilter === 'all' || contract.status === statusFilter
      
      return matchesSearch && matchesStatus
    })
    
    setFilteredContracts(filtered)
  }, [contracts, searchQuery, statusFilter])

  const loadContracts = async () => {
    setLoading(true)
    try {
      // TODO: Replace with actual API call
      // const response = await fetch('/api/contracts')
      // const data = await response.json()
      // setContracts(data)
      
      // Mock delay
      setTimeout(() => {
        setContracts(mockContracts)
        setLoading(false)
      }, 500)
    } catch (error) {
      console.error('Error loading contracts:', error)
      setLoading(false)
    }
  }

  const loadVessels = async () => {
    try {
      // TODO: Replace with actual API call
      // const response = await fetch('/api/vessels')
      // const data = await response.json()
      // setVessels(data)
      
      setVessels(mockVessels)
    } catch (error) {
      console.error('Error loading vessels:', error)
    }
  }

  const handleCreateContract = async () => {
    try {
      // TODO: Replace with actual API call
      // const response = await fetch('/api/contracts', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(newContract)
      // })
      
      // Mock contract creation
      const vessel = vessels.find(v => v.id === newContract.vesselId)
      const mockNewContract = {
        id: `contract-${Date.now()}`,
        vesselId: newContract.vesselId,
        vesselName: vessel?.name || 'Unknown Vessel',
        energyAmount: parseFloat(newContract.energyAmount),
        pricePerKwh: parseFloat(newContract.pricePerKwh),
        totalValue: parseFloat(newContract.energyAmount) * parseFloat(newContract.pricePerKwh),
        startTime: newContract.startTime,
        endTime: newContract.endTime,
        status: 'pending',
        createdAt: new Date().toISOString(),
        terms: newContract.terms
      }
      
      setContracts(prev => [mockNewContract, ...prev])
      setIsCreateModalOpen(false)
      setNewContract({
        vesselId: '',
        energyAmount: '',
        pricePerKwh: '',
        startTime: '',
        endTime: '',
        terms: ''
      })
      
      alert('Contract created successfully!')
    } catch (error) {
      console.error('Error creating contract:', error)
      alert('Failed to create contract')
    }
  }

  const handleContractAction = async (contractId, action) => {
    try {
      // TODO: Replace with actual API calls
      switch (action) {
        case 'cancel':
          setContracts(prev => 
            prev.map(contract => 
              contract.id === contractId 
                ? { ...contract, status: 'cancelled' }
                : contract
            )
          )
          break
        case 'complete':
          setContracts(prev => 
            prev.map(contract => 
              contract.id === contractId 
                ? { ...contract, status: 'completed' }
                : contract
            )
          )
          break
        default:
          break
      }
    } catch (error) {
      console.error(`Error ${action} contract:`, error)
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800'
      case 'pending':
        return 'bg-yellow-100 text-yellow-800'
      case 'completed':
        return 'bg-blue-100 text-blue-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      case 'cancelled':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active':
        return <CheckCircle className="h-4 w-4" />
      case 'pending':
        return <Clock className="h-4 w-4" />
      case 'completed':
        return <CheckCircle className="h-4 w-4" />
      case 'failed':
        return <AlertCircle className="h-4 w-4" />
      case 'cancelled':
        return <X className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  const formatDateTime = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  // Check admin access
  if (user?.role_name !== 'ADMIN') {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Access Denied</h3>
          <p className="text-gray-600">You need administrator privileges to access contract management.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Smart Contracts</h1>
          <p className="text-gray-600 mt-2">Manage vessel-to-grid energy transaction contracts</p>
        </div>
        
        <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
          <DialogTrigger asChild>
            <Button className="flex items-center space-x-2">
              <Plus className="h-4 w-4" />
              <span>Create Contract</span>
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Create New Contract</DialogTitle>
              <DialogDescription>
                Set up a new vessel-to-grid energy transaction contract
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="vessel">Vessel</Label>
                <Select 
                  value={newContract.vesselId} 
                  onChange={(value) => setNewContract(prev => ({ ...prev, vesselId: value }))}
                  placeholder="Select vessel"
                >
                  {vessels.map(vessel => (
                    <option key={vessel.id} value={vessel.id}>
                      {vessel.name} ({vessel.owner})
                    </option>
                  ))}
                </Select>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="energyAmount">Energy Amount (kWh)</Label>
                  <Input
                    id="energyAmount"
                    type="number"
                    value={newContract.energyAmount}
                    onChange={(e) => setNewContract(prev => ({ ...prev, energyAmount: e.target.value }))}
                    placeholder="150"
                  />
                </div>
                <div>
                  <Label htmlFor="pricePerKwh">Price per kWh ($)</Label>
                  <Input
                    id="pricePerKwh"
                    type="number"
                    step="0.01"
                    value={newContract.pricePerKwh}
                    onChange={(e) => setNewContract(prev => ({ ...prev, pricePerKwh: e.target.value }))}
                    placeholder="0.15"
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="startTime">Start Time</Label>
                  <Input
                    id="startTime"
                    type="datetime-local"
                    value={newContract.startTime}
                    onChange={(e) => setNewContract(prev => ({ ...prev, startTime: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="endTime">End Time</Label>
                  <Input
                    id="endTime"
                    type="datetime-local"
                    value={newContract.endTime}
                    onChange={(e) => setNewContract(prev => ({ ...prev, endTime: e.target.value }))}
                  />
                </div>
              </div>
              
              <div>
                <Label htmlFor="terms">Terms & Conditions</Label>
                <Textarea
                  id="terms"
                  value={newContract.terms}
                  onChange={(e) => setNewContract(prev => ({ ...prev, terms: e.target.value }))}
                  placeholder="Contract terms and conditions..."
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateContract}>
                Create Contract
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search and Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input
                placeholder="Search by vessel name or contract ID..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant={statusFilter === 'all' ? 'default' : 'outline'}
                onClick={() => setStatusFilter('all')}
                size="sm"
              >
                All
              </Button>
              <Button
                variant={statusFilter === 'active' ? 'default' : 'outline'}
                onClick={() => setStatusFilter('active')}
                size="sm"
              >
                Active
              </Button>
              <Button
                variant={statusFilter === 'pending' ? 'default' : 'outline'}
                onClick={() => setStatusFilter('pending')}
                size="sm"
              >
                Pending
              </Button>
              <Button
                variant={statusFilter === 'completed' ? 'default' : 'outline'}
                onClick={() => setStatusFilter('completed')}
                size="sm"
              >
                Completed
              </Button>
              <Button
                variant={statusFilter === 'failed' ? 'default' : 'outline'}
                onClick={() => setStatusFilter('failed')}
                size="sm"
              >
                Failed
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Contracts List */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-8">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">Loading contracts...</p>
          </div>
        ) : filteredContracts.length === 0 ? (
          <Card>
            <CardContent className="text-center py-8">
              <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Contracts Found</h3>
              <p className="text-gray-600">
                {searchQuery || statusFilter !== 'all' 
                  ? 'No contracts match your current filters.' 
                  : 'No contracts have been created yet.'}
              </p>
            </CardContent>
          </Card>
        ) : (
          filteredContracts.map((contract) => (
            <Card key={contract.id} className="hover:shadow-lg transition-shadow">
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="space-y-3 flex-1">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-lg font-semibold flex items-center space-x-2">
                          <span>{contract.vesselName}</span>
                          <Badge className={`${getStatusColor(contract.status)} flex items-center space-x-1`}>
                            {getStatusIcon(contract.status)}
                            <span>{contract.status.charAt(0).toUpperCase() + contract.status.slice(1)}</span>
                          </Badge>
                        </h3>
                        <p className="text-sm text-gray-600">Contract ID: {contract.id}</p>
                      </div>
                      <div className="text-right">
                        <p className="text-lg font-bold text-green-600">${contract.totalValue.toFixed(2)}</p>
                        <p className="text-sm text-gray-600">${contract.pricePerKwh}/kWh</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                      <div>
                        <span className="font-medium text-gray-900">Energy Amount:</span>
                        <p className="text-gray-600">{contract.energyAmount} kWh</p>
                      </div>
                      <div>
                        <span className="font-medium text-gray-900">Time Window:</span>
                        <p className="text-gray-600">
                          {formatDateTime(contract.startTime)} - {formatDateTime(contract.endTime)}
                        </p>
                      </div>
                      <div>
                        <span className="font-medium text-gray-900">Created:</span>
                        <p className="text-gray-600">{formatDateTime(contract.createdAt)}</p>
                      </div>
                    </div>

                    <div>
                      <span className="font-medium text-gray-900 text-sm">Terms:</span>
                      <p className="text-sm text-gray-600 mt-1">{contract.terms}</p>
                    </div>

                    <div className="flex items-center space-x-2 pt-2">
                      <Button variant="outline" size="sm">
                        <FileText className="h-4 w-4 mr-1" />
                        View Details
                      </Button>
                      
                      {contract.status === 'pending' && (
                        <>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => handleContractAction(contract.id, 'cancel')}
                          >
                            <X className="h-4 w-4 mr-1" />
                            Cancel
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => handleContractAction(contract.id, 'complete')}
                          >
                            <CheckCircle className="h-4 w-4 mr-1" />
                            Mark Complete
                          </Button>
                        </>
                      )}
                      
                      {contract.status === 'active' && (
                        <Button 
                          variant="outline" 
                          size="sm"
                          onClick={() => handleContractAction(contract.id, 'complete')}
                        >
                          <CheckCircle className="h-4 w-4 mr-1" />
                          Mark Complete
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}

export default ContractsManagement