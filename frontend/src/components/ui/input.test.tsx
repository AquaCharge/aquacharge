import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Input } from './input'
import { describe, test, expect } from 'vitest'

describe('Input Component', () => {
  test('renders input with placeholder', () => {
    render(<Input placeholder="Enter text" />)
    const inputElement = screen.getByPlaceholderText('Enter text')
    expect(inputElement).toBeInTheDocument()
  })

  test('allows text input', async () => {
    const user = userEvent.setup()
    render(<Input />)
    const inputElement = screen.getByRole('textbox')
    await user.type(inputElement, 'Hello World')
    expect(inputElement).toHaveValue('Hello World')
  })
})
