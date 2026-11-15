import React, { useEffect, useState } from 'react';
import { dateTime, LoadingState, transformDataFrame, type PanelData, type PanelProps, type QueryRunner } from '@grafana/data';
import { createQueryRunner, PanelRenderer } from '@grafana/runtime';
import type { Subscription } from 'rxjs';

import type { AdaptiveTableOptions } from '../adaptive-types';

const REFRESH_MS = 30_000;
const TIMEOUT_MS = 15_000;

type Snapshot = { data?: PanelData; evaluatedAt?: number; error?: string };

export const CurrentPanel: React.FC<PanelProps<AdaptiveTableOptions>> = (props) => {
  const view = props.options.currentView;
  const [snapshot, setSnapshot] = useState<Snapshot>({});
  // QueryRunner resolves Grafana variables normally. This key only detects scope changes.
  const scope = props.replaceVariables(JSON.stringify(view?.queries ?? []));
  const requestId = props.data.request?.requestId;
  const windowMs = view?.pluginId === 'timeseries'
    ? props.timeRange.to.valueOf() - props.timeRange.from.valueOf()
    : 15 * 60_000;

  useEffect(() => {
    if (!view) { return; }
    let stopped = false;
    let generation = 0;
    let runner: QueryRunner | undefined;
    let subscription: Subscription | undefined;
    let transformed: Subscription | undefined;
    let deadline: ReturnType<typeof setTimeout> | undefined;

    const cancel = () => {
      if (deadline) { clearTimeout(deadline); }
      transformed?.unsubscribe();
      subscription?.unsubscribe();
      runner?.destroy();
    };
    const refresh = () => {
      cancel();
      const active = ++generation;
      let failed = false;
      const evaluatedAt = Date.now();
      if (!Number.isFinite(windowMs) || windowMs <= 0) {
        setSnapshot({ error: 'UNKNOWN — invalid current observation window' });
        return;
      }
      const range = {
        from: dateTime(evaluatedAt - windowMs),
        to: dateTime(evaluatedAt),
        raw: { from: dateTime(evaluatedAt - windowMs), to: dateTime(evaluatedAt) },
      };
      const fail = (message: string) => {
        if (!stopped && active === generation) {
          failed = true;
          if (deadline) { clearTimeout(deadline); }
          setSnapshot({ error: message });
        }
      };
      setSnapshot({});
      deadline = setTimeout(() => {
        // A timed-out response must never repopulate a current verdict later.
        fail('CURRENT source unavailable — query timed out');
        ++generation;
        cancel();
      }, TIMEOUT_MS);
      try {
        runner = createQueryRunner();
        subscription = runner.get().subscribe({
          next: (data) => {
            if (stopped || failed || active !== generation) { return; }
            if (data.state === LoadingState.Error || (data.errors?.length ?? 0) > 0) {
              fail('CURRENT source unavailable — query failed');
              return;
            }
            if (data.state !== LoadingState.Done) { return; }
            const responseTime = data.request?.range?.to.valueOf() ?? data.timeRange?.to.valueOf();
            if (responseTime !== evaluatedAt) {
              fail('UNKNOWN — current query time could not be verified');
              return;
            }
            transformed?.unsubscribe();
            transformed = transformDataFrame(view.transformations, data.series, {
              interpolate: props.replaceVariables,
            }).subscribe({
              next: (series) => {
                if (stopped || failed || active !== generation) { return; }
                if (deadline) { clearTimeout(deadline); }
                if (Date.now() - evaluatedAt > TIMEOUT_MS) {
                  fail('UNKNOWN — current response is stale');
                  return;
                }
                setSnapshot({ data: { ...data, series, timeRange: range }, evaluatedAt });
              },
              error: () => fail('CURRENT source unavailable — transformation failed'),
            });
          },
          error: () => fail('CURRENT source unavailable — query failed'),
        });
        runner.run({
          datasource: { type: 'prometheus', uid: 'prometheus' },
          queries: view.queries,
          panelId: props.id,
          timezone: props.timeZone,
          timeRange: range,
          maxDataPoints: 1000,
          minInterval: '30s',
          cacheTimeout: '0',
          queryCachingTTL: 0,
        });
      } catch {
        fail('CURRENT source unavailable — query engine unavailable');
      }
    };
    refresh();
    const timer = setInterval(refresh, REFRESH_MS);
    const onVisible = () => { if (document.visibilityState === 'visible') { refresh(); } };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      stopped = true;
      ++generation;
      clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
      cancel();
    };
  // Query changes are represented by scope; a dashboard refresh gets a new request ID.
  // The selected historical time range never becomes the current query range.
  }, [view, scope, requestId, windowMs, props.id, props.timeZone, props.replaceVariables]);

  if (!view) { return <div role="alert">UNKNOWN — current view is not configured</div>; }
  if (snapshot.error) { return <div role="alert">{snapshot.error}</div>; }
  if (!snapshot.data) { return <output>Loading CURRENT observations…</output>; }
  if (!snapshot.data.series.some((frame) => frame.length > 0)) {
    return <div>UNKNOWN — no current observations</div>;
  }
  if (!PanelRenderer) { return <div role="alert">CURRENT source unavailable — renderer unavailable</div>; }
  const clock = new Date(snapshot.evaluatedAt ?? 0).toISOString();
  return (
    <div data-bioetl-current-query="verified" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div title={'Query evaluated at ' + clock + '; publication time is separate'} style={{ fontSize: 16, lineHeight: '20px', overflowWrap: 'anywhere' }}>
        {clock.slice(0, 16).replace('T', ' ') + ' UTC'}
      </div>
      <div style={{ flex: 1, minHeight: 0 }}>
        <PanelRenderer
          pluginId={view.pluginId === 'table' && view.compactFields ? 'bioetl-selectorshell-panel' : view.pluginId}
          data={snapshot.data}
          title={props.title}
          options={view.compactFields
            ? { ...view.options, viewMode: 'rows', compactFields: view.compactFields }
            : view.options}
          fieldConfig={props.fieldConfig}
          timeZone={props.timeZone}
          width={props.width}
          height={Math.max(0, props.height - 20)}
        />
      </div>
    </div>
  );
};
