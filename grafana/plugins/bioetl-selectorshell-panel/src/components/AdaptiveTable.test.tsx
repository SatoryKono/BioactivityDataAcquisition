import React from 'react';
import { fireEvent, render, screen, within } from '@testing-library/react';
import type { DataFrame, Field, FieldType, LoadingState, PanelProps } from '@grafana/data';

import { defaultOptions } from '../types';
import type { AdaptiveTableOptions } from '../adaptive-types';
import { AdaptiveTable } from './AdaptiveTable';

jest.mock('@grafana/ui', () => {
  const Modal = Object.assign(
    ({ children, title }: { children: React.ReactNode; title: string }) => <section role="dialog" aria-label={title}>{children}</section>,
    { ButtonRow: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }
  );
  return {
    Table: ({ data }: { data: { fields: Array<{ name: string }> } }) => <div data-testid="native-table">{data.fields.map((f) => f.name).join(',')}</div>,
    Modal,
    Button: ({ children, onClick, disabled, 'aria-label': label }: React.ButtonHTMLAttributes<HTMLButtonElement>) =>
      <button onClick={onClick} disabled={disabled} aria-label={label}>{children}</button>,
  };
});
jest.mock('@grafana/ui/unstable', () => ({
  TableNG: ({ data }: { data: { fields: Array<{ name: string; config: { displayName?: string } }> } }) => <div data-testid="native-table">{data.fields.map((f) => f.config.displayName ?? f.name).join(',')}</div>,
}));

const ids = [
  '29ff0c5a-c5e4-5d67-ad8c-37b492404fde',
  '24231b65-d913-5a32-bbc0-65fbfef01716',
  '7771872e-9c87-51a5-9ae9-6c07ab05eb07',
];
const names = ['Workflow', 'Pipeline', 'Provider', 'Run ID', 'Started', 'Duration', 'Overview', 'Saved Evidence', 'Data Quality', 'Replay Readiness'];

function viewport(width: number) {
  Object.defineProperty(window, 'innerWidth', { configurable: true, value: width });
  fireEvent(window, new Event('resize'));
}

beforeEach(() => viewport(584));

function props(): PanelProps<AdaptiveTableOptions> {
  const frame: DataFrame = {
    length: ids.length,
    fields: [
      ...names.map((name) => ({
        name,
        type: 'string' as FieldType,
        config: {},
        values: name === 'Run ID' ? ids.map((id) => id.slice(0, 8)) : [`${name} one`, `${name} two`, `${name} three`],
      })),
      { name: 'run_id', type: 'string' as FieldType, values: ids, config: { custom: { hidden: true } } },
      { name: 'run_type', type: 'string' as FieldType, values: ['backfill', 'backfill', 'backfill'], config: { custom: { hidden: true } } },
    ],
  };
  frame.fields.find((f) => f.name === 'Run ID')!.getLinks = (({ valueRowIndex }: { valueRowIndex: number }) => [
    { href: `/d/run?var-run_id=${ids[valueRowIndex]}`, title: 'Select this run', target: '_self' },
    { href: `/report/${ids[valueRowIndex]}`, title: 'Open report', target: '_self' },
  ]) as Field['getLinks'];
  return {
    title: 'Inspect Recent Runs',
    data: { state: 'Done' as LoadingState, series: [frame] },
    options: { ...defaultOptions, viewMode: 'runs' },
    width: 468,
    height: 340,
    replaceVariables: () => 'scope-a',
    fieldConfig: { defaults: {}, overrides: [] },
  } as unknown as PanelProps<AdaptiveTableOptions>;
}

it('keeps all ten fields and every returned run accessible without widening the compact view', () => {
  render(<AdaptiveTable {...props()} />);
  const table = screen.getByRole('table', { name: 'Selected catalog row' });
  for (const name of names) {
    expect(within(table).getByRole('rowheader', { name })).toBeInTheDocument();
  }
  expect(screen.getByRole('link', { name: ids[0].slice(0, 8) })).toHaveAttribute('href', `/d/run?var-run_id=${ids[0]}`);
  expect(screen.getByRole('button', { name: 'Previous run' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Next run' }));
  fireEvent.click(screen.getByRole('button', { name: 'Next run' }));
  expect(screen.getByText('3 / 3')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Next run' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Details' }));
  const modal = screen.getByRole('dialog', { name: 'Run details' });
  expect(within(modal).getByText(ids[2])).toBeInTheDocument();
  expect(within(modal).getByText('backfill')).toBeInTheDocument();
  expect(within(modal).getByRole('link', { name: ids[2].slice(0, 8) })).toHaveAttribute('href', `/d/run?var-run_id=${ids[2]}`);
  expect(within(modal).getByRole('link', { name: 'Open report' })).toHaveAttribute('href', `/report/${ids[2]}`);
});

it('keeps a 1920-pixel display at 200 percent zoom readable at 960 CSS pixels', () => {
  viewport(960);
  render(<AdaptiveTable {...props()} width={628} />);
  expect(screen.getByRole('table', { name: 'Selected catalog row' })).toBeInTheDocument();
  expect(screen.getAllByRole('rowheader')).toHaveLength(10);
  expect(screen.queryByTestId('native-table')).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: 'Details' }));
  expect(within(screen.getByRole('dialog')).getByText(ids[0])).toBeInTheDocument();
});

it('returns to the native table at a wide size without dropping fields or identity metadata', () => {
  const panelProps = props();
  const view = render(<AdaptiveTable {...panelProps} />);
  viewport(1920);
  view.rerender(<AdaptiveTable {...panelProps} width={1500} />);
  const table = screen.getByTestId('native-table');
  for (const name of names) {
    expect(table).toHaveTextContent(name);
  }
  expect(table).not.toHaveTextContent('run_id');
  expect(table).not.toHaveTextContent('run_type');
  expect(panelProps.data.series[0].fields.find((field) => field.name === 'run_id')?.values).toEqual(ids);
  expect(panelProps.data.series[0].fields.find((field) => field.name === 'Run ID')?.getLinks?.({ valueRowIndex: 2 })[0].href).toBe(`/d/run?var-run_id=${ids[2]}`);
  expect(screen.queryByRole('navigation', { name: 'Catalog pagination' })).not.toBeInTheDocument();
});

it.each(['displayName', 'displayNameFromDS'] as const)('uses Grafana %s labels and keeps hidden identity out of the summary', (property) => {
  const panelProps = props();
  const frame = panelProps.data.series[0];
  frame.fields[0].config[property] = 'Workflow';
  frame.fields[0].name = 'workflow_id';
  render(<AdaptiveTable {...panelProps} />);
  expect(screen.getByRole('rowheader', { name: 'Workflow' })).toBeInTheDocument();
  expect(screen.queryByRole('rowheader', { name: 'workflow_id' })).not.toBeInTheDocument();
  expect(screen.queryByRole('rowheader', { name: 'run_id' })).not.toBeInTheDocument();
});

it('retains datasource aliases in the wide grid without renaming its raw identity fields', () => {
  viewport(1920);
  const panelProps = props();
  const field = panelProps.data.series[0].fields[0];
  field.name = 'workflow_id';
  field.config.displayNameFromDS = 'Workflow';
  render(<AdaptiveTable {...panelProps} width={1500} />);
  expect(screen.getByTestId('native-table')).toHaveTextContent('Workflow');
  expect(screen.getByTestId('native-table')).not.toHaveTextContent('workflow_id');
  expect(field.name).toBe('workflow_id');
  expect(field.config.displayName).toBeUndefined();
});

it('clears an old page and full detail when the dashboard scope changes', () => {
  const panelProps = props();
  const view = render(<AdaptiveTable {...panelProps} />);
  fireEvent.click(screen.getByRole('button', { name: 'Next run' }));
  fireEvent.click(screen.getByRole('button', { name: 'Details' }));
  view.rerender(<AdaptiveTable {...panelProps} replaceVariables={() => 'scope-b'} />);
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(screen.getByText('1 / 3')).toBeInTheDocument();
});

it('replaces previous successful data with a visible source error and removes old details', () => {
  const panelProps = props();
  const view = render(<AdaptiveTable {...panelProps} />);
  fireEvent.click(screen.getByRole('button', { name: 'Details' }));
  view.rerender(<AdaptiveTable {...panelProps} data={{ ...panelProps.data, state: 'Error' as LoadingState, errors: [{ message: 'backend unavailable' }] }} />);
  expect(screen.getByRole('alert')).toHaveTextContent('Source unavailable · backend unavailable');
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
});

it('keeps empty results distinct from a successful state and from a loading request', () => {
  const panelProps = props();
  const view = render(<AdaptiveTable {...panelProps} data={{ ...panelProps.data, series: [] }} />);
  expect(screen.getByText('UNKNOWN · No matching data')).toBeInTheDocument();
  expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
  view.rerender(<AdaptiveTable {...panelProps} data={{ ...panelProps.data, state: 'Loading' as LoadingState }} />);
  expect(screen.getByRole('status')).toHaveTextContent('Loading');
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

it('reports a failed request even when Grafana provides no error details', () => {
  const panelProps = props();
  render(<AdaptiveTable {...panelProps} data={{ ...panelProps.data, state: 'Error' as LoadingState, errors: undefined }} />);
  expect(screen.getByRole('alert')).toHaveTextContent('Source unavailable · Query failed');
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
});

it('does not count a valid-empty sentinel as a launch or offer actions for a missing identity', () => {
  const panelProps = props();
  const frame = panelProps.data.series[0];
  frame.length = 1;
  for (const field of frame.fields) {
    field.values = [field.name === 'Pipeline' ? 'VALID EMPTY' : ''];
  }
  render(<AdaptiveTable {...panelProps} />);
  expect(screen.getByText('VALID EMPTY · No matching launches')).toBeInTheDocument();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
  expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
});

it('keeps secondary evidence in details when the compact summary selects fewer fields', () => {
  const panelProps = props();
  panelProps.options = { ...panelProps.options, viewMode: 'rows', compactFields: ['Pipeline', 'Overview'] };
  render(<AdaptiveTable {...panelProps} />);
  expect(screen.getAllByRole('rowheader')).toHaveLength(2);
  fireEvent.click(screen.getByRole('button', { name: 'Next row' }));
  fireEvent.click(screen.getByRole('button', { name: 'Details' }));
  const modal = screen.getByRole('dialog', { name: 'Full context' });
  expect(within(modal).getByText('Saved Evidence')).toBeInTheDocument();
  expect(within(modal).getByText(ids[1])).toBeInTheDocument();
  expect(within(modal).getByRole('link', { name: 'Open report' })).toHaveAttribute('href', `/report/${ids[1]}`);
});

it('reports an incomplete required summary rather than rendering partial success', () => {
  const panelProps = props();
  panelProps.options = { ...panelProps.options, viewMode: 'rows', compactFields: ['Pipeline', 'Missing required status'] };
  render(<AdaptiveTable {...panelProps} />);
  expect(screen.getByText('UNKNOWN · Required fields unavailable')).toBeInTheDocument();
  expect(screen.queryByRole('table')).not.toBeInTheDocument();
  expect(screen.queryByRole('link')).not.toBeInTheDocument();
});

it('shows complete object values instead of an object placeholder', () => {
  const panelProps = props();
  panelProps.data.series[0].fields.find((field) => field.name === 'Pipeline')!.values[0] = { name: 'pipeline-a', stages: ['bronze', 'silver'] };
  render(<AdaptiveTable {...panelProps} />);
  expect(screen.getByText('{"name":"pipeline-a","stages":["bronze","silver"]}')).toBeInTheDocument();
  expect(screen.queryByText('[object Object]')).not.toBeInTheDocument();
});

it('keeps a nonserializable value unknown without crashing the remaining record', () => {
  const panelProps = props();
  const cyclic: Record<string, unknown> = {};
  cyclic.self = cyclic;
  panelProps.data.series[0].fields.find((field) => field.name === 'Pipeline')!.values[0] = cyclic;
  render(<AdaptiveTable {...panelProps} />);
  expect(screen.getByText('UNKNOWN')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: ids[0].slice(0, 8) })).toHaveAttribute('href', `/d/run?var-run_id=${ids[0]}`);
});

it.each([
  [123, '123'],
  [false, 'false'],
  [BigInt(23), '23'],
  [Symbol('value'), 'Symbol(value)'],
])('retains the primitive cell value %p as %s', (value, text) => {
  const panelProps = props();
  panelProps.data.series[0].fields.find((field) => field.name === 'Pipeline')!.values[0] = value;
  render(<AdaptiveTable {...panelProps} />);
  expect(screen.getByText(text as string)).toBeInTheDocument();
});
