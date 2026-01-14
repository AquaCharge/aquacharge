import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, test, expect, vi } from 'vitest'
import StationDetailsCard from './StationDetailsCard'

// Mock the child components to avoid complex dependencies
vi.mock('@/components/ui/card', () => ({
  Card: ({ children }: { children: React.ReactNode }) => <div data-testid="card">{children}</div>,
  CardContent: ({ children }: { children: React.ReactNode }) => <div data-testid="card-content">{children}</div>,
  CardHeader: ({ children }: { children: React.ReactNode }) => <div data-testid="card-header">{children}</div>,
  CardTitle: ({ children }: { children: React.ReactNode }) => <h3 data-testid="card-title">{children}</h3>,
}))

vi.mock('@/components/ui/badge', () => ({
  Badge: ({ children, variant }: { children: React.ReactNode; variant?: string }) => (
    <span data-testid="badge" data-variant={variant}>{children}</span>
  ),
}))

vi.mock('@/components/ui/button', () => ({
  Button: ({ children, onClick, disabled }: { children: React.ReactNode; onClick?: () => void; disabled?: boolean }) => (
    <button onClick={onClick} disabled={disabled} data-testid="button">
      {children}
    </button>
  ),
}))

// Mock Lucide React icon
vi.mock('lucide-react', () => ({
  X: () => <span data-testid="x-icon">×</span>,
}))

describe('StationDetailsCard', () => {
  const mockStation = {
    name: 'Test Station',
    status: 'active' as const,
    availableChargers: 2,
    totalChargers: 4,
    chargerTypes: ['Type 1', 'Type 2', 'CCS'],
  }

  const mockOnClose = vi.fn()
  const mockOnReserve = vi.fn()

  test('renders station information correctly', () => {
    render(
      <StationDetailsCard 
        station={mockStation} 
        onClose={mockOnClose}
        onReserve={mockOnReserve}
      />
    )

    expect(screen.getByText('Test Station')).toBeInTheDocument()
    expect(screen.getByText('Limited Availability')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText(/of 4/)).toBeInTheDocument()
    expect(screen.getByText('active')).toBeInTheDocument()
    expect(screen.getByText('Type 1')).toBeInTheDocument()
    expect(screen.getByText('Type 2')).toBeInTheDocument()
    expect(screen.getByText('CCS')).toBeInTheDocument()
  })

  test('displays correct availability status', () => {
    const { rerender } = render(
      <StationDetailsCard station={mockStation} onClose={mockOnClose} onReserve={mockOnReserve} />
    )
    expect(screen.getByText('Limited Availability')).toBeInTheDocument()

    rerender(
      <StationDetailsCard 
        station={{ ...mockStation, status: 'maintenance' }} 
        onClose={mockOnClose} 
        onReserve={mockOnReserve} 
      />
    )
    expect(screen.getByText('Under Maintenance')).toBeInTheDocument()

    rerender(
      <StationDetailsCard 
        station={{ ...mockStation, availableChargers: 0 }} 
        onClose={mockOnClose} 
        onReserve={mockOnReserve} 
      />
    )
    expect(screen.getByText('Fully Occupied')).toBeInTheDocument()

    rerender(
      <StationDetailsCard 
        station={{ ...mockStation, availableChargers: 4 }} 
        onClose={mockOnClose} 
        onReserve={mockOnReserve} 
      />
    )
    expect(screen.getByText('All Available')).toBeInTheDocument()
  })

  test('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup()
    render(
      <StationDetailsCard 
        station={mockStation} 
        onClose={mockOnClose}
        onReserve={mockOnReserve}
      />
    )

    const buttons = screen.getAllByTestId('button')
    await user.click(buttons[0])

    expect(mockOnClose).toHaveBeenCalledTimes(1)
  })

  test('calls onReserve when reserve button is clicked', async () => {
    const user = userEvent.setup()
    render(
      <StationDetailsCard 
        station={mockStation} 
        onClose={mockOnClose}
        onReserve={mockOnReserve}
      />
    )

    const buttons = screen.getAllByTestId('button')
    const reserveButton = buttons.find(button => button.textContent === 'Reserve Charging Slot')
    await user.click(reserveButton!)

    expect(mockOnReserve).toHaveBeenCalledTimes(1)
    expect(mockOnReserve).toHaveBeenCalledWith(mockStation)
  })

  test('disables reserve button when no chargers available', () => {
    render(
      <StationDetailsCard 
        station={{ ...mockStation, availableChargers: 0 }} 
        onClose={mockOnClose}
        onReserve={mockOnReserve}
      />
    )

    const buttons = screen.getAllByTestId('button')
    const reserveButton = buttons.find(button => button.textContent === 'Reserve Charging Slot')
    expect(reserveButton).toBeDisabled()
  })

  test('disables reserve button when station is not active', () => {
    render(
      <StationDetailsCard 
        station={{ ...mockStation, status: 'maintenance' }} 
        onClose={mockOnClose}
        onReserve={mockOnReserve}
      />
    )

    const buttons = screen.getAllByTestId('button')
    const reserveButton = buttons.find(button => button.textContent === 'Reserve Charging Slot')
    expect(reserveButton).toBeDisabled()
  })

  test('enables reserve button when station is active and has available chargers', () => {
    render(
      <StationDetailsCard 
        station={mockStation} 
        onClose={mockOnClose}
        onReserve={mockOnReserve}
      />
    )

    const buttons = screen.getAllByTestId('button')
    const reserveButton = buttons.find(button => button.textContent === 'Reserve Charging Slot')
    expect(reserveButton).not.toBeDisabled()
  })
})