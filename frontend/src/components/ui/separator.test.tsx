import { render } from '@testing-library/react'
import { Separator } from './separator'
import { test, expect } from 'vitest'

test('renders Separator component correctly', () => {
  const { container } = render(<Separator />)
  expect(container.firstChild).toHaveAttribute('data-orientation', 'horizontal')
})

test('supports vertical orientation', () => {
  const { container } = render(<Separator orientation="vertical" />)
  expect(container.firstChild).toHaveAttribute('data-orientation', 'vertical')
})
