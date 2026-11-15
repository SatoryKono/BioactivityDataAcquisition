import React from 'react';
import { act, render, screen } from '@testing-library/react';
import { Subject } from 'rxjs';
import { dateTime, LoadingState, type PanelData, type PanelProps, type QueryRunnerOptions } from '@grafana/data';
import { createQueryRunner } from '@grafana/runtime';
import type { AdaptiveTableOptions } from '../adaptive-types';
import { CurrentPanel } from './CurrentPanel';

jest.mock('@grafana/data', () => {
  const { of } = jest.requireActual<typeof import('rxjs')>('rxjs');
  return {
    LoadingState: { Done: 'Done', Error: 'Error' },
    dateTime: (value: number) => ({ valueOf: () => value, toISOString: () => new Date(value).toISOString() }),
    transformDataFrame: jest.fn((_options, frames) => of(frames)),
  };
});
jest.mock('@grafana/runtime', () => ({
  createQueryRunner: jest.fn(),
  PanelRenderer: ({ data, fieldConfig }: { data: PanelData; fieldConfig: unknown }) =>
    <div data-testid="current-native">{JSON.stringify({ series: data.series, fieldConfig })}</div>,
}));

const now = Date.parse('2026-11-13T20:00:00Z');
const runners: Array<{ events: Subject<PanelData>; run: jest.Mock; destroy: jest.Mock }> = [];
function props(): PanelProps<AdaptiveTableOptions> {
  return {
    id: 9701, title: 'CURRENT', width: 800, height: 300, timeZone: 'utc',
    timeRange: { from: dateTime(now - 2 * 86400_000), to: dateTime(now - 86400_000) },
    data: { state: LoadingState.Done, series: [{ length: 1, fields: [] }], request: { requestId: 'history-1' } },
    options: { currentView: {
      pluginId: 'table', queries: [{ refId: 'A', expr: 'current_metric{pipeline="$pipeline"}' }],
      transformations: [{ id: 'organize', options: {} }], options: { showHeader: true },
    } },
    replaceVariables: (value: string) => value.replace('$pipeline', 'chembl_activity'),
    fieldConfig: { defaults: { noValue: 'UNKNOWN', unit: 's' }, overrides: [] },
  } as unknown as PanelProps<AdaptiveTableOptions>;
}
function done(index: number, value: number, end?: number) {
  const range = (runners[index].run.mock.calls[0][0] as QueryRunnerOptions).timeRange;
  runners[index].events.next({
    state: LoadingState.Done,
    timeRange: end === undefined ? range : { ...range, to: dateTime(end) },
    series: [{ length: 1, fields: [{ name: 'Value', type: 'number', values: [value], config: {} }] }],
  } as PanelData);
}
beforeEach(() => {
  jest.useFakeTimers();
  jest.setSystemTime(now);
  runners.length = 0;
  jest.mocked(createQueryRunner).mockImplementation(() => {
    const runner = { events: new Subject<PanelData>(), run: jest.fn(), destroy: jest.fn(), cancel: jest.fn() };
    runners.push(runner);
    return { ...runner, get: () => runner.events };
  });
});
afterEach(() => { jest.clearAllTimers(); jest.useRealTimers(); });

it('queries now without historical input and retains units and the original query', () => {
  const panel = props();
  render(<CurrentPanel {...panel} />);
  const request = runners[0].run.mock.calls[0][0] as QueryRunnerOptions;
  expect(request.timeRange.to.valueOf()).toBe(now);
  expect(request.timeRange.from.valueOf()).toBe(now - 15 * 60_000);
  expect(request.queries).toEqual(panel.options.currentView!.queries);
  expect(screen.queryByTestId('current-native')).not.toBeInTheDocument();
  act(() => done(0, 42));
  expect(screen.getByTestId('current-native')).toHaveTextContent('"values":[42]');
  expect(screen.getByTestId('current-native')).toHaveTextContent('"unit":"s"');
  expect(screen.getByText('2026-11-13 20:00 UTC')).toBeInTheDocument();
});
it('keeps the current clock when only the historical period changes', () => {
  const panel = props();
  const view = render(<CurrentPanel {...panel} />);
  view.rerender(<CurrentPanel {...panel} timeRange={{ ...panel.timeRange, to: dateTime(now - 7 * 86400_000) }} />);
  expect(runners).toHaveLength(1);
  act(() => done(0, 42));
  expect(screen.getByTestId('current-native')).toHaveTextContent('"values":[42]');
});
it('cancels refresh generations and rejects late old data', () => {
  render(<CurrentPanel {...props()} />);
  act(() => done(0, 42));
  act(() => jest.advanceTimersByTime(30_000));
  expect(runners[0].destroy).toHaveBeenCalled();
  act(() => done(0, 999));
  expect(screen.queryByTestId('current-native')).not.toBeInTheDocument();
  act(() => done(1, 7));
  expect(screen.getByTestId('current-native')).toHaveTextContent('"values":[7]');
  expect(screen.getByTestId('current-native')).not.toHaveTextContent('999');
});
it('rejects a response evaluated at the historical end', () => {
  render(<CurrentPanel {...props()} />);
  act(() => done(0, 0, now - 86400_000));
  expect(screen.getByRole('alert')).toHaveTextContent('current query time could not be verified');
});
it('clears a previous scope before accepting the replacement scope', () => {
  const panel = props();
  const view = render(<CurrentPanel {...panel} />);
  act(() => done(0, 42));
  view.rerender(<CurrentPanel {...panel} replaceVariables={(value) => value.replace('$pipeline', 'chembl_assay')} />);
  expect(runners[0].destroy).toHaveBeenCalled();
  expect(screen.queryByTestId('current-native')).not.toBeInTheDocument();
  act(() => done(0, 999));
  expect(screen.queryByTestId('current-native')).not.toBeInTheDocument();
  act(() => done(1, 7));
  expect(screen.getByTestId('current-native')).toHaveTextContent('"values":[7]');
});
it('keeps empty data unknown', () => {
  render(<CurrentPanel {...props()} />);
  const range = (runners[0].run.mock.calls[0][0] as QueryRunnerOptions).timeRange;
  act(() => runners[0].events.next({ state: LoadingState.Done, series: [], timeRange: range }));
  expect(screen.getByText('UNKNOWN — no current observations')).toBeInTheDocument();
});
it('clears an error without exposing backend details or accepting late data', () => {
  render(<CurrentPanel {...props()} />);
  act(() => done(0, 42));
  act(() => runners[0].events.next({ state: LoadingState.Error, series: [], errors: [{ message: 'private backend details' }] } as unknown as PanelData));
  expect(screen.getByRole('alert')).toHaveTextContent('CURRENT source unavailable');
  expect(screen.queryByText('private backend details')).not.toBeInTheDocument();
  act(() => done(0, 0));
  expect(screen.queryByTestId('current-native')).not.toBeInTheDocument();
});
it('times out without accepting a late healthy-looking response', () => {
  render(<CurrentPanel {...props()} />);
  act(() => jest.advanceTimersByTime(15_001));
  expect(screen.getByRole('alert')).toHaveTextContent('query timed out');
  act(() => done(0, 0));
  expect(screen.queryByTestId('current-native')).not.toBeInTheDocument();
});
it('retains current trend duration while moving its end to now', () => {
  const panel = props();
  panel.options.currentView!.pluginId = 'timeseries';
  render(<CurrentPanel {...panel} />);
  const request = runners[0].run.mock.calls[0][0] as QueryRunnerOptions;
  expect(request.timeRange.to.valueOf()).toBe(now);
  expect(request.timeRange.to.valueOf() - request.timeRange.from.valueOf()).toBe(86400_000);
});
