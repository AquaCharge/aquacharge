import { render } from '@testing-library/react'
import { Skeleton } from './skeleton'
import { describe, expect, it } from 'vitest'

describe('Skeleton Component', () => {
  it('renders with base styling', () => {
    const { container } = render(<Skeleton />)
    expect(container.firstChild).toHaveClass('animate-pulse')
  })

  it('merges custom class names', () => {
    const { getByTestId } = render(
      <Skeleton data-testid="skeleton" className="custom-class" />
    )
    expect(getByTestId('skeleton')).toHaveClass('custom-class')
  })
})
