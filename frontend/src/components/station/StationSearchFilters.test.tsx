import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import StationSearchFilters from './StationSearchFilters'

// Simple mocks with proper TypeScript types
vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => (
    <button onClick={onClick}>{children}</button>
  ),
}))

vi.mock('@/components/ui/input', () => ({
  Input: ({ 
    value, 
    onChange, 
    placeholder 
  }: { 
    value: string; 
    onChange: (e: React.ChangeEvent<HTMLInputElement>) => void; 
    placeholder?: string; 
  }) => (
    <input 
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      data-testid="search-input"
    />
  ),
}))

vi.mock('lucide-react', () => ({
  Search: () => <span>🔍</span>,
  Filter: () => <span>⚡</span>,
  X: () => <span>×</span>,
}))

// Mock fetch to avoid API calls entirely
globalThis.fetch = vi.fn(() => 
  Promise.resolve({
    json: () => Promise.resolve([]),
  } as Response)
)

describe('StationSearchFilters', () => {
  const mockStations = [
    { 
      id: 1, 
      name: 'Downtown Station', 
      availableChargers: 3, 
      totalChargers: 8, 
      status: 'active', 
      chargerTypes: ['Type 2', 'CCS'] 
    },
  ] as any

  const mockOnStationSelect = vi.fn()
  const mockOnFilterChange = vi.fn()

  test('renders search input and filter buttons', () => {
    render(<StationSearchFilters stations={mockStations} />)

    expect(screen.getByPlaceholderText('Search stations or locations...')).toBeInTheDocument()
    expect(screen.getByText('Available Only')).toBeInTheDocument()
    expect(screen.getByText('Type 2')).toBeInTheDocument()
    expect(screen.getByText('CCS')).toBeInTheDocument()
  })

  test('searches for stations by name', async () => {
    const user = userEvent.setup()
    render(<StationSearchFilters stations={mockStations} />)

    await user.type(screen.getByTestId('search-input'), 'Downtown')

    expect(await screen.findByText('Downtown Station')).toBeInTheDocument()
    expect(screen.getByText('3 available')).toBeInTheDocument()
  })

  test('selects station from search results', async () => {
    const user = userEvent.setup()
    render(<StationSearchFilters stations={mockStations} onStationSelect={mockOnStationSelect} />)

    await user.type(screen.getByTestId('search-input'), 'Downtown')
    await user.click(await screen.findByText('Downtown Station'))

    expect(mockOnStationSelect).toHaveBeenCalledWith(mockStations[0])
  })

  test('toggles available only filter', async () => {
    const user = userEvent.setup()
    render(<StationSearchFilters stations={mockStations} onFilterChange={mockOnFilterChange} />)

    await user.click(screen.getByText('Available Only'))

    expect(mockOnFilterChange).toHaveBeenCalledWith({
      availableOnly: true,
      chargerTypes: [],
      maxDistance: null,
    })
  })

  test('toggles charger type filter', async () => {
    const user = userEvent.setup()
    render(<StationSearchFilters stations={mockStations} onFilterChange={mockOnFilterChange} />)

    await user.click(screen.getByText('Type 2'))

    expect(mockOnFilterChange).toHaveBeenCalledWith({
      availableOnly: false,
      chargerTypes: ['Type 2'],
      maxDistance: null,
    })
  })

  test('clears search input', async () => {
    const user = userEvent.setup()
    render(<StationSearchFilters stations={mockStations} />)

    const input = screen.getByTestId('search-input')
    await user.type(input, 'test')
    
    const clearButton = screen.getByText('×').closest('button')
    await user.click(clearButton!)

    expect(input).toHaveValue('')
  })
})