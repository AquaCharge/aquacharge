import { render, screen } from '@testing-library/react'
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardAction,
} from './card'
import { describe, expect, it } from 'vitest'

describe('Card component', () => {
  it('renders composed sections', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Test Card</CardTitle>
          <CardDescription>This is a test card.</CardDescription>
        </CardHeader>
        <CardContent>Body content</CardContent>
        <CardAction>Action</CardAction>
        <CardFooter>Footer</CardFooter>
      </Card>
    )

    expect(screen.getByText('Test Card')).toBeInTheDocument()
    expect(screen.getByText('This is a test card.')).toBeInTheDocument()
    expect(screen.getByText('Body content')).toBeInTheDocument()
    expect(screen.getByText('Action')).toBeInTheDocument()
    expect(screen.getByText('Footer')).toBeInTheDocument()
  })

  it('merges custom class names', () => {
    render(<Card data-testid="card" className="custom-card" />)
    expect(screen.getByTestId('card')).toHaveClass('custom-card')
  })
})
