import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from './dialog'
import { test, expect } from 'vitest'

const TestDialog = () => {
  const [open, setOpen] = React.useState(false)

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger>Open Dialog</DialogTrigger>
      <DialogContent>
        <DialogTitle>Dialog Title</DialogTitle>
        <DialogDescription>Dialog Content</DialogDescription>
      </DialogContent>
    </Dialog>
  )
}

test('Dialog opens and closes correctly', async () => {
  const user = userEvent.setup()
  render(<TestDialog />)

  await user.click(screen.getByText('Open Dialog'))
  expect(screen.getByText('Dialog Content')).toBeInTheDocument()

  await user.click(screen.getByRole('button', { name: /close/i }))
  await waitFor(() =>
    expect(screen.queryByText('Dialog Content')).not.toBeInTheDocument()
  )
})
