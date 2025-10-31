import { render, screen } from '@testing-library/react'
import {
  Tooltip,
  TooltipProvider,
  TooltipTrigger,
  TooltipContent,
} from './tooltip'
import { test, expect } from 'vitest'

test('displays tooltip on hover', () => {
  render(
    <TooltipProvider delayDuration={0}>
      <Tooltip defaultOpen>
        <TooltipTrigger asChild>
          <button type="button">Hover over me</button>
        </TooltipTrigger>
        <TooltipContent>Tooltip text</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )

  expect(screen.getByRole('tooltip', { name: 'Tooltip text' })).toBeInTheDocument()
})
