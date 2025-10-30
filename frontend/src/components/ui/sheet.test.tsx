import { render, screen } from '@testing-library/react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from './sheet'
import { test, expect } from 'vitest'

test('renders Sheet content when open', () => {
  render(
    <Sheet defaultOpen>
      <SheetContent data-testid="sheet-content">
        <SheetHeader>
          <SheetTitle>Panel Title</SheetTitle>
          <SheetDescription>Panel description</SheetDescription>
        </SheetHeader>
      </SheetContent>
    </Sheet>
  )

  expect(screen.getByTestId('sheet-content')).toBeInTheDocument()
  expect(screen.getByText('Panel Title')).toBeInTheDocument()
})

test('applies side variants', () => {
  render(
    <Sheet defaultOpen>
      <SheetContent data-testid="left-sheet" side="left">
        <SheetHeader>
          <SheetTitle>Left Sheet</SheetTitle>
          <SheetDescription>Left content</SheetDescription>
        </SheetHeader>
      </SheetContent>
    </Sheet>
  )

  expect(screen.getByTestId('left-sheet').className).toContain('left-0')
})
