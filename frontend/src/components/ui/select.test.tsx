import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Select } from './select'

const Trigger = ({ isOpen, setIsOpen }) => (
  <button type="button" onClick={() => setIsOpen(!isOpen)}>
    {isOpen ? 'Close menu' : 'Open menu'}
  </button>
)

const Option = ({ value, selectedValue, setSelectedValue }) => (
  <button
    type="button"
    onClick={() => setSelectedValue(value)}
    data-selected={selectedValue === value}
  >
    {value}
  </button>
)

describe('Select Component', () => {
  it('toggles open state via provided children', async () => {
    const user = userEvent.setup()
    render(
      <Select>
        <Trigger />
      </Select>
    )

    const toggle = screen.getByRole('button', { name: /open menu/i })
    await user.click(toggle)
    expect(toggle).toHaveTextContent('Close menu')
  })

  it('updates selected value when child calls setter', async () => {
    const user = userEvent.setup()
    render(
      <Select>
        <Trigger />
        <Option value="Option 1" />
        <Option value="Option 2" />
      </Select>
    )

    const option = screen.getByRole('button', { name: 'Option 2' })
    await user.click(option)
    expect(option).toHaveAttribute('data-selected', 'true')
  })
})
