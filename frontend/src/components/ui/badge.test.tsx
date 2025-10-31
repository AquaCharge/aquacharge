import { render, screen } from '@testing-library/react'
import { Badge } from './badge'
import { test, expect } from 'vitest'

test('renders Badge component with text', () => {
  render(<Badge>Test Badge</Badge>)
  const badgeElement = screen.getByText(/Test Badge/i)
  expect(badgeElement).toBeInTheDocument()
})

test('renders Badge component with correct class', () => {
  render(<Badge className="custom-class">Test Badge</Badge>)
  const badgeElement = screen.getByText(/Test Badge/i)
  expect(badgeElement).toHaveClass('custom-class')
})
