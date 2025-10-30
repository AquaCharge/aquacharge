import { render, screen } from '@testing-library/react'
import { Button } from './button'
import { describe, test, expect } from 'vitest'

describe('Button component', () => {
  test('renders button with text', () => {
    render(<Button>Click Me</Button>)
    const buttonElement = screen.getByText(/click me/i)
    expect(buttonElement).toBeInTheDocument()
  })

  test('applies variant styling', () => {
    render(<Button variant="secondary">Styled</Button>)
    const buttonElement = screen.getByText(/styled/i)
    expect(buttonElement.className).toContain('bg-secondary')
  })
})
