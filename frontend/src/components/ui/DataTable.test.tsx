import { render, screen } from '@testing-library/react';
import DataTable from './DataTable';

interface Row {
  id: number;
  name: string;
  value: number | null;
}

const columns = [
  { key: 'name', header: 'Nombre' },
  { key: 'value', header: 'Valor' },
];

describe('DataTable', () => {
  it('renders headers from the columns config', () => {
    render(
      <DataTable<Row> columns={columns} data={[]} keyExtractor={(r) => r.id} />,
    );
    expect(screen.getByText('Nombre')).toBeInTheDocument();
    expect(screen.getByText('Valor')).toBeInTheDocument();
  });

  it('shows the empty-state row when data is empty', () => {
    const { container } = render(
      <DataTable<Row> columns={columns} data={[]} keyExtractor={(r) => r.id} />,
    );
    expect(screen.getByText('No hay datos disponibles')).toBeInTheDocument();
    // colSpan matches the number of columns.
    const emptyCell = container.querySelector('td[colspan]');
    expect(emptyCell?.getAttribute('colspan')).toBe(String(columns.length));
  });

  it('renders one row per item and stringifies raw cell values', () => {
    const data: Row[] = [
      { id: 1, name: 'alpha', value: 42 },
      { id: 2, name: 'beta', value: 7 },
    ];
    render(
      <DataTable<Row>
        columns={columns}
        data={data}
        keyExtractor={(r) => r.id}
      />,
    );
    expect(screen.getByText('alpha')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('beta')).toBeInTheDocument();
  });

  it('renders the em-dash fallback when a raw cell value is null/undefined', () => {
    const data: Row[] = [{ id: 1, name: 'alpha', value: null }];
    render(
      <DataTable<Row>
        columns={columns}
        data={data}
        keyExtractor={(r) => r.id}
      />,
    );
    expect(screen.getByText('—')).toBeInTheDocument();
  });

  it('uses the column render() when provided', () => {
    const customColumns = [
      {
        key: 'name',
        header: 'Nombre',
        render: (r: Row) => (
          <strong data-testid="strong">{r.name.toUpperCase()}</strong>
        ),
      },
    ];
    const data: Row[] = [{ id: 1, name: 'alpha', value: 1 }];
    render(
      <DataTable<Row>
        columns={customColumns}
        data={data}
        keyExtractor={(r) => r.id}
      />,
    );
    expect(screen.getByTestId('strong')).toHaveTextContent('ALPHA');
  });
});
