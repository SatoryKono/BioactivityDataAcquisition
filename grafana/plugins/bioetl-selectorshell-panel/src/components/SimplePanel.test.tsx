import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import { locationService } from '@grafana/runtime';

import { defaultOptions, SelectorContextPayload } from '../types';
import { SimplePanel } from './SimplePanel';

jest.mock('@grafana/runtime', () => ({ locationService: { partial: jest.fn() } }));
jest.mock('@grafana/ui', () => ({
  useStyles2: () => ({ wrapper: 'wrapper', code: 'code' }),
  Stack: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Text: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
  Button: ({ children }: { children: React.ReactNode }) => <button>{children}</button>,
}));

function props(path = '/selector-context'): React.ComponentProps<typeof SimplePanel> {
  return {
    options: { ...defaultOptions, selectorContextPath: path },
    replaceVariables: (value: string) => (value.includes('run_id') ? 'run-123' : 'chembl'),
  } as React.ComponentProps<typeof SimplePanel>;
}

function response(runId = 'run-123'): Response {
  const payload: SelectorContextPayload = {
    contract: 'control_plane_selector_context_v1',
    resolved_via: 'selected_run_id',
    selected: { workflow: 'chembl', pipeline: 'chembl', run_type: 'backfill', run_id: runId },
  };
  return { ok: true, json: async () => payload } as Response;
}

function deferredResponse() {
  let resolve!: (value: Response) => void;
  const promise = new Promise<Response>((complete) => {
    resolve = complete;
  });
  return { promise, resolve };
}

describe('selector context request lifecycle', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    jest.clearAllMocks();
  });

  it('refreshes a changed run with the same replaceVariables function', async () => {
    let runId = 'run-123';
    const replaceVariables = (value: string) => (value.includes('run_id') ? runId : 'chembl');
    const fetchMock = jest.fn().mockResolvedValue(response());
    global.fetch = fetchMock;
    const panelProps = { ...props(), replaceVariables };
    const view = render(<SimplePanel {...panelProps} />);
    await screen.findByText(/Resolved run-123/);
    runId = 'run-456';
    fetchMock.mockResolvedValue(response(runId));
    view.rerender(<SimplePanel {...panelProps} />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      '/selector-context?run_id=run-456', expect.objectContaining({ credentials: 'same-origin' })
    ));
    await screen.findByText(/Resolved run-456/);
  });

  it('shows loading until the current request resolves', async () => {
    const request = deferredResponse();
    global.fetch = jest.fn().mockReturnValue(request.promise);
    render(<SimplePanel {...props()} />);
    expect(screen.getByText('Syncing…')).toBeInTheDocument();
    await act(async () => request.resolve(response()));
    await waitFor(() => expect(screen.queryByText('Syncing…')).not.toBeInTheDocument());
    expect(screen.getByText(/Resolved run-123/)).toBeInTheDocument();
  });

  it('hides the previous error while a new URL is loading', async () => {
    const pending = deferredResponse();
    global.fetch = jest.fn().mockRejectedValueOnce(new Error('request failed')).mockReturnValueOnce(pending.promise);
    const view = render(<SimplePanel {...props()} />);
    expect(await screen.findByText('request failed')).toBeInTheDocument();
    view.rerender(<SimplePanel {...props('/new-selector-context')} />);
    expect(screen.queryByText('request failed')).not.toBeInTheDocument();
    expect(screen.getByText('Syncing…')).toBeInTheDocument();
    await act(async () => pending.resolve(response()));
    await waitFor(() => expect(screen.queryByText('Syncing…')).not.toBeInTheDocument());
  });

  it('ignores a late response from an aborted request', async () => {
    const previous = deferredResponse();
    const current = deferredResponse();
    const fetchMock = jest.fn().mockReturnValueOnce(previous.promise).mockReturnValueOnce(current.promise);
    global.fetch = fetchMock;
    const view = render(<SimplePanel {...props()} />);
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    view.rerender(<SimplePanel {...props('/new-selector-context')} />);
    expect(init.signal?.aborted).toBe(true);
    await act(async () => previous.resolve(response()));
    expect(screen.getByText('Syncing…')).toBeInTheDocument();
    expect(locationService.partial).not.toHaveBeenCalled();
    await act(async () => current.resolve(response()));
    await waitFor(() => expect(screen.queryByText('Syncing…')).not.toBeInTheDocument());
    expect(locationService.partial).toHaveBeenCalledTimes(1);
  });
});
