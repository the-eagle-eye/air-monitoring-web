import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import EquipoForm from './EquipoForm';

describe('EquipoForm', () => {
  it('renders all fields with defaults in create mode', () => {
    render(
      <EquipoForm mode="create" onSubmit={jest.fn()} onCancel={jest.fn()} />,
    );
    expect(screen.getByLabelText(/Device ID/)).toBeInTheDocument();
    expect(screen.getByLabelText('Nombre')).toBeInTheDocument();
    expect(screen.getByLabelText('Tipo')).toBeInTheDocument();
    expect(screen.getByLabelText('Ubicacion')).toBeInTheDocument();
    expect(screen.getByLabelText('Criticidad')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Crear Equipo' }),
    ).toBeInTheDocument();
  });

  it('shows the "Guardar Cambios" button in edit mode with device_id disabled', () => {
    render(
      <EquipoForm
        mode="edit"
        initialData={{ device_id: 'T101', nombre: 'Est-A' }}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
      />,
    );
    const dev = screen.getByLabelText(/Device ID/) as HTMLInputElement;
    expect(dev.disabled).toBe(true);
    expect(dev.value).toBe('T101');
    expect((screen.getByLabelText('Nombre') as HTMLInputElement).value).toBe(
      'Est-A',
    );
    expect(
      screen.getByRole('button', { name: 'Guardar Cambios' }),
    ).toBeInTheDocument();
  });

  it('submits only non-empty fields', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    const usr = userEvent.setup();
    render(
      <EquipoForm mode="create" onSubmit={onSubmit} onCancel={jest.fn()} />,
    );
    await usr.type(screen.getByLabelText(/Device ID/), 'T999');
    await usr.type(screen.getByLabelText('Nombre'), 'Nueva');
    await usr.click(screen.getByRole('button', { name: 'Crear Equipo' }));
    expect(onSubmit).toHaveBeenCalledWith({
      device_id: 'T999',
      nombre: 'Nueva',
      criticidad: 'media',
    });
  });

  it('calls onCancel when the Cancelar button is clicked', async () => {
    const onCancel = jest.fn();
    const usr = userEvent.setup();
    render(
      <EquipoForm mode="create" onSubmit={jest.fn()} onCancel={onCancel} />,
    );
    await usr.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(onCancel).toHaveBeenCalled();
  });

  it('renders an error message when onSubmit rejects', async () => {
    const onSubmit = jest.fn().mockRejectedValue(new Error('boom'));
    const usr = userEvent.setup();
    render(
      <EquipoForm mode="create" onSubmit={onSubmit} onCancel={jest.fn()} />,
    );
    await usr.type(screen.getByLabelText(/Device ID/), 'T999');
    await act(async () => {
      await usr.click(screen.getByRole('button', { name: 'Crear Equipo' }));
    });
    expect(await screen.findByText('boom')).toBeInTheDocument();
  });

  it('changes the criticidad via the select', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    const usr = userEvent.setup();
    render(
      <EquipoForm mode="create" onSubmit={onSubmit} onCancel={jest.fn()} />,
    );
    await usr.type(screen.getByLabelText(/Device ID/), 'T-1');
    await usr.selectOptions(screen.getByLabelText('Criticidad'), 'alta');
    await usr.click(screen.getByRole('button', { name: 'Crear Equipo' }));
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({ criticidad: 'alta' }),
    );
  });
});
