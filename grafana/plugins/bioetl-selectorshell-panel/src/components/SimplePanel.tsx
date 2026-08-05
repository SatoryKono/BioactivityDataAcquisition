import React, { useEffect, useMemo, useRef, useState } from 'react';
import { PanelProps } from '@grafana/data';
import { locationService } from '@grafana/runtime';
import { Button, Stack, Text, useStyles2 } from '@grafana/ui';
import { css } from '@emotion/css';

import {
  buildNextShellUpdate,
  buildSelectorContextUrl,
  hasExactRunSelection,
  summarizeSyncState,
} from '../sync';
import {
  defaultOptions,
  SelectorContextPayload,
  SelectorShellOptions,
  VisibleSelectorState,
} from '../types';

interface Props extends PanelProps<SelectorShellOptions> {}

function getStyles() {
  return {
    wrapper: css`
      display: flex;
      flex-direction: column;
      gap: 8px;
      height: 100%;
      padding: 8px 10px;
      overflow: auto;
    `,
    code: css`
      font-family: monospace;
      font-size: 12px;
      white-space: pre-wrap;
      word-break: break-word;
      padding: 8px;
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.04);
    `,
  };
}

export const SimplePanel: React.FC<Props> = ({ options, replaceVariables }) => {
  const styles = useStyles2(getStyles);
  const mergedOptions = { ...defaultOptions, ...options };
  const [payload, setPayload] = useState<SelectorContextPayload | null>(null);
  const [error, setError] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const appliedSignatureRef = useRef<string>('');

  const current = useMemo<VisibleSelectorState>(
    () => ({
      workflow: replaceVariables('${workflow:text}'),
      pipeline: replaceVariables('${pipeline:text}'),
      runType: replaceVariables('${run_type:text}'),
      runId: replaceVariables('${run_id:text}'),
    }),
    [replaceVariables]
  );

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError('');

    const url = buildSelectorContextUrl(mergedOptions.selectorContextPath, {
      runId: current.runId,
      workflow: current.workflow,
      pipeline: current.pipeline,
      runType: current.runType,
    });

    fetch(url, {
      credentials: 'same-origin',
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`selector-context HTTP ${response.status}`);
        }
        const nextPayload = (await response.json()) as SelectorContextPayload;
        setPayload(nextPayload);

        const nextUpdate = buildNextShellUpdate(current, nextPayload, {
          applyRunId: hasExactRunSelection(current.runId),
          allowLastRunDefaults: mergedOptions.autoApplyLastRunDefaults,
        });

        // Exact-run path also requires autoApplyExactRunContext.
        if (
          nextPayload.resolved_via === 'selected_run_id' &&
          !mergedOptions.autoApplyExactRunContext
        ) {
          return;
        }
        if (nextUpdate == null) {
          return;
        }
        const signature = JSON.stringify(nextUpdate);
        if (appliedSignatureRef.current === signature) {
          return;
        }
        appliedSignatureRef.current = signature;
        locationService.partial(nextUpdate, true);
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const message = reason instanceof Error ? reason.message : String(reason);
        setError(message);
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      });

    return () => controller.abort();
  }, [
    current,
    mergedOptions.autoApplyExactRunContext,
    mergedOptions.autoApplyLastRunDefaults,
    mergedOptions.selectorContextPath,
  ]);

  const resolvedText = summarizeSyncState(current, payload);

  const onManualApply = () => {
    if (payload == null) {
      return;
    }
    const nextUpdate = buildNextShellUpdate(current, payload, {
      applyRunId: true,
      allowLastRunDefaults: true,
    });
    if (nextUpdate == null) {
      return;
    }
    appliedSignatureRef.current = JSON.stringify(nextUpdate);
    locationService.partial(nextUpdate, true);
  };

  return (
    <div className={styles.wrapper}>
      <Stack direction="column" gap={0.5}>
        <Text variant="bodySmall" color="secondary">
          BioETL selector shell
        </Text>
        <Text variant="body">{isLoading ? 'Syncing…' : resolvedText}</Text>
        {error ? (
          <Text variant="bodySmall" color="error">
            {error}
          </Text>
        ) : null}
        {!mergedOptions.autoApplyExactRunContext || !mergedOptions.autoApplyLastRunDefaults ? (
          <Button size="sm" variant="secondary" onClick={onManualApply} disabled={payload == null}>
            Apply selector context
          </Button>
        ) : null}
        {mergedOptions.showDebugDetails && payload != null ? (
          <pre className={styles.code}>{JSON.stringify(payload, null, 2)}</pre>
        ) : null}
      </Stack>
    </div>
  );
};
