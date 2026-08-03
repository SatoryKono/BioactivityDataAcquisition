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
    const runId = current.runId;
    if (!hasExactRunSelection(runId)) {
      setPayload(null);
      setError('');
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    setIsLoading(true);
    setError('');

    fetch(buildSelectorContextUrl(mergedOptions.selectorContextPath, runId), {
      credentials: 'same-origin',
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`selector-context HTTP ${response.status}`);
        }
        const nextPayload = (await response.json()) as SelectorContextPayload;
        setPayload(nextPayload);

        if (!mergedOptions.autoApplyExactRunContext) {
          return;
        }
        const nextUpdate = buildNextShellUpdate(current, nextPayload);
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
  }, [current, mergedOptions.autoApplyExactRunContext, mergedOptions.selectorContextPath]);

  const resolvedText = summarizeSyncState(current, payload);

  return (
    <div className={styles.wrapper}>
      <Stack direction="column" gap={0.5}>
        <Text variant="bodySmall" color="secondary">
          Visible shell
        </Text>
        <div className={styles.code}>
          {`workflow=${current.workflow}\npipeline=${current.pipeline}\nrun_type=${current.runType}\nrun_id=${current.runId}`}
        </div>
      </Stack>

      <Stack direction="column" gap={0.5}>
        <Text variant="bodySmall" color="secondary">
          Exact-run sync
        </Text>
        <Text variant="bodySmall">{resolvedText}</Text>
        {isLoading && <Text variant="bodySmall">Loading selector-context…</Text>}
        {error !== '' && <Text variant="bodySmall">Error: {error}</Text>}
      </Stack>

      {!mergedOptions.autoApplyExactRunContext && hasExactRunSelection(current.runId) && payload && (
        <Button
          size="sm"
          onClick={() => {
            const nextUpdate = buildNextShellUpdate(current, payload);
            if (nextUpdate != null) {
              locationService.partial(nextUpdate, true);
            }
          }}
        >
          Apply exact run context
        </Button>
      )}

      {mergedOptions.showDebugDetails && payload && (
        <Stack direction="column" gap={0.5}>
          <Text variant="bodySmall" color="secondary">
            selector-context payload
          </Text>
          <div className={styles.code}>{JSON.stringify(payload, null, 2)}</div>
        </Stack>
      )}
    </div>
  );
};
