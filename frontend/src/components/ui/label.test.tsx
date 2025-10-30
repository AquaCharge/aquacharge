import { render, screen } from '@testing-library/react'
import { Label } from './label'
import { test, expect } from 'vitest'

test('displays the correct text', () => {
  render(<Label>Test Label</Label>)
  const labelElement = screen.getByText(/Test Label/i)
  expect(labelElement).toBeInTheDocument()
})
