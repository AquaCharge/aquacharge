import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {
  SidebarProvider,
  Sidebar,
  SidebarContent,
  useSidebar,
} from './sidebar'
import { describe, test, expect } from 'vitest'
const SidebarStateViewer = () => {
  const { state, toggleSidebar } = useSidebar()

  return (
    <div>
      <span data-testid="sidebar-state">{state}</span>
      <button type="button" onClick={toggleSidebar}>
        Toggle
      </button>
    </div>
  )
}

describe('Sidebar', () => {
  test('renders Sidebar content within provider', () => {
    render(
      <SidebarProvider>
        <Sidebar>
          <SidebarContent>
            <div>Sidebar Body</div>
          </SidebarContent>
        </Sidebar>
      </SidebarProvider>
    )

    expect(screen.getByText('Sidebar Body')).toBeInTheDocument()
  })

  test('toggleSidebar updates state', async () => {
    const user = userEvent.setup()
    render(
      <SidebarProvider>
        <SidebarStateViewer />
      </SidebarProvider>
    )

    const state = screen.getByTestId('sidebar-state')
    expect(state).toHaveTextContent('expanded')

    await user.click(screen.getByRole('button', { name: /toggle/i }))
    expect(state).toHaveTextContent('collapsed')
  })
})
