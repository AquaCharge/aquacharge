import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Textarea } from './textarea'
import { describe, test, expect } from 'vitest'

describe('Textarea Component', () => {
  test('renders correctly', () => {
    render(<Textarea />)
    const textareaElement = screen.getByRole('textbox')
    expect(textareaElement).toBeInTheDocument()
  })

  test('allows text input', async () => {
    const user = userEvent.setup()
    render(<Textarea />)
    const textareaElement = screen.getByRole('textbox')
    await user.type(textareaElement, 'Hello World')
    expect(textareaElement).toHaveValue('Hello World')
  })
})
