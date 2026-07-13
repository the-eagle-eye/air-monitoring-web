import { render, screen } from '@testing-library/react';
import Home from './page';

describe('Home page', () => {
  it('renders the main heading', () => {
    render(<Home />);
    expect(
      screen.getByRole('heading', { name: /Sistema de Monitoreo Predictivo/i }),
    ).toBeInTheDocument();
  });
});
