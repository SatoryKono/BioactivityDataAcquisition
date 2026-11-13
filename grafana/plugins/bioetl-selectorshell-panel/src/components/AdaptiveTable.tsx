import React, { useLayoutEffect, useMemo, useState, useSyncExternalStore } from 'react';
import type { DataFrame, Field, PanelProps } from '@grafana/data';
import { Button, Modal } from '@grafana/ui';
import { TableNG as Table } from '@grafana/ui/unstable';
import { css } from '@emotion/css';

import type { AdaptiveTableOptions } from '../adaptive-types';

const shell = css`
  width: 100%;
  height: 100%;
  font-size: 16px;
  line-height: 20px;
  & a, & button, & [role='gridcell'], & [role='columnheader'] { font-size: 16px; }
`;
const nativeShell = css`
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
`;
const compact = css`
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 4px;
  box-sizing: border-box;
  & table { width: 100%; border-collapse: collapse; table-layout: fixed; }
  & th, & td { padding: 0 4px; vertical-align: top; text-align: left; overflow-wrap: anywhere; }
  & th { width: 36%; font-weight: 600; }
`;
const pager = css`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 4px;
`;
const details = css`
  font-size: 16px;
  line-height: 24px;
  & dl { display: grid; grid-template-columns: minmax(100px, 35%) minmax(0, 1fr); gap: 8px; }
  & dt { font-weight: 600; }
  & dd { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
`;
const more = css`
  border: 0;
  background: transparent;
  color: inherit;
  padding: 0 4px;
  line-height: 20px;
  font-size: 16px;
  cursor: pointer;
`;
const detailNames: Record<string, string> = { run_id: 'Full Run ID', pipeline: 'Full pipeline', run_type: 'Run Type', workflow_scope: 'Workflow scope' };

function hidden(field: Field): boolean {
  return field.config.custom?.hidden === true || field.config.custom?.hideFrom?.viz === true;
}

function label(field: Field): string {
  return field.config.displayName ?? field.config.displayNameFromDS ?? field.state?.displayName ?? field.name;
}

function subscribeViewport(listener: () => void) {
  window.addEventListener('resize', listener);
  return () => window.removeEventListener('resize', listener);
}

function rawValueText(raw: unknown): string {
  if (typeof raw === 'object') {
    try { return JSON.stringify(raw) ?? 'UNKNOWN'; }
    catch { return 'UNKNOWN'; }
  }
  if (typeof raw === 'string') { return raw; }
  if (typeof raw === 'number' || typeof raw === 'bigint' || typeof raw === 'boolean' || typeof raw === 'symbol') {
    return raw.toString();
  }
  return raw === undefined ? 'undefined' : 'UNKNOWN';
}

function previewText(name: string, full: string, preview: boolean): string {
  if (preview && name === 'Context') { return full.split(' · ')[0]; }
  if (preview && name === 'Value' && full.length > 44) { return `${full.slice(0, 16)}…${full.slice(-12)}`; }
  return full;
}

function valueText(field: Field, row: number): string {
  const raw: unknown = field.values[row];
  if (raw == null) {
    return field.config.noValue ?? 'UNKNOWN';
  }
  const display = field.display?.(raw);
  return display ? `${display.prefix ?? ''}${display.text}${display.suffix ?? ''}` : rawValueText(raw);
}

function Value({ field, row, preview = false, allLinks = false }: Readonly<{ field: Field; row: number; preview?: boolean; allLinks?: boolean }>) {
  const full = valueText(field, row);
  // The full value remains in the explicit details view. Do not CSS-clip data.
  const text = previewText(label(field), full, preview);
  const colored = ['color-text', 'color-background'].includes(field.config.custom?.cellOptions?.type);
  const color = colored ? field.display?.(field.values[row])?.color : undefined;
  const links = field.getLinks?.({ valueRowIndex: row })?.filter((item) => item.href && !item.href.includes('${')) ?? [];
  const link = links[0];
  return <>
    {link ? <a href={link.href} title={full} target={link.target} rel="noopener noreferrer" style={{ color }}>{text}</a>
      : <span title={full} style={{ color }}>{text}</span>}
    {allLinks ? links.slice(1).map((item) => <React.Fragment key={`${item.title}:${item.href}`}>
      {' · '}<a href={item.href} target={item.target} rel="noopener noreferrer">{item.title}</a>
    </React.Fragment>) : null}
  </>;
}

function orderedRows(frame: DataFrame | undefined, sortBy: AdaptiveTableOptions['sortBy']): number[] {
  const indices = Array.from({ length: frame?.length ?? 0 }, (_, index) => index);
  const sort = sortBy?.[0];
  const field = frame?.fields.find((item) => label(item) === sort?.displayName);
  if (field && sort) {
    indices.sort((left, right) => {
      const a: unknown = field.values[left];
      const b: unknown = field.values[right];
      const cmp = typeof a === 'number' && typeof b === 'number' ? a - b : rawValueText(a).localeCompare(rawValueText(b));
      return sort.desc ? -cmp : cmp;
    });
  }
  return indices;
}

type CompactRowsProps = Readonly<{
  fields: Field[]; row: number; isRuns: boolean; isPaged: boolean; title: string;
  currentPage: number; rowCount: number;
  onPageChange: (page: number) => void; onDetails: (row: number) => void;
}>;

function CompactRows({fields, row, isRuns, isPaged, title, currentPage, rowCount, onPageChange, onDetails}: CompactRowsProps) {
  return (
        <>
          <table aria-label={isRuns ? 'Selected catalog row' : title}>
            <tbody>{fields.map((field, index) => (
              <tr key={field.name}>
                <th scope="row">{label(field)}{!isPaged && index === 0 ? (
                  <button className={more} aria-label="Open full details" title="Full details" onClick={() => onDetails(row)}>⋯</button>
                ) : null}</th>
                <td><Value field={field} row={row} preview={!isRuns} /></td>
              </tr>
            ))}</tbody>
          </table>
          {isPaged ? (
            <nav className={pager} aria-label={isRuns ? 'Catalog pagination' : 'Evidence pagination'}>
              <Button size="sm" variant="secondary" aria-label={isRuns ? 'Previous run' : 'Previous row'} disabled={currentPage === 0} onClick={() => onPageChange(currentPage - 1)}>Previous</Button>
              <span aria-live="polite">{currentPage + 1} / {rowCount}</span>
              <Button size="sm" variant="secondary" onClick={() => onDetails(row)}>Details</Button>
              <Button size="sm" variant="secondary" aria-label={isRuns ? 'Next run' : 'Next row'} disabled={currentPage === rowCount - 1} onClick={() => onPageChange(currentPage + 1)}>Next</Button>
            </nav>
          ) : null}
        </>
  );
}

function queryStatus(data: PanelProps<AdaptiveTableOptions>['data']): React.ReactNode {
  if (data.state === 'Error' || (data.errors?.length ?? 0) > 0) {
    return <div className={shell} role="alert">Source unavailable · {data.errors?.[0]?.message ?? 'Query failed'}</div>;
  }
  if (data.state === 'Loading' || data.state === 'NotStarted') {
    return <output className={shell} style={{ display: 'block' }}>Loading…</output>;
  }
  return null;
}

function RunDetails({fields, row, isRuns, onDismiss}: Readonly<{
  fields: Field[]; row: number | null; isRuns: boolean; onDismiss: () => void;
}>) {
  if (row === null) { return null; }
  return (
    <Modal title={isRuns ? 'Run details' : 'Full context'} isOpen onDismiss={onDismiss}>
      <div className={details}>
        <dl>{fields.map((field) => (
          <React.Fragment key={field.name}>
            <dt>{detailNames[field.name] ?? label(field)}</dt>
            <dd><Value field={field} row={row} allLinks /></dd>
          </React.Fragment>
        ))}</dl>
      </div>
      <Modal.ButtonRow><Button onClick={onDismiss}>Close</Button></Modal.ButtonRow>
    </Modal>
  );
}

const AdaptiveTableView: React.FC<PanelProps<AdaptiveTableOptions>> = (props) => {
  const { data, width, height, options, fieldConfig, timeRange } = props;
  const [page, setPage] = useState(0);
  const [detailRow, setDetailRow] = useState<number | null>(null);
  const [host, setHost] = useState<HTMLDivElement | null>(null);
  const [bounds, setBounds] = useState<{ width: number; height: number } | null>(null);
  useLayoutEffect(() => {
    if (!host || typeof ResizeObserver === 'undefined') { return; }
    const observer = new ResizeObserver(() => {
      if (host.clientWidth && host.clientHeight) {
        setBounds({ width: host.clientWidth, height: host.clientHeight });
      }
    });
    observer.observe(host);
    return () => observer.disconnect();
  }, [host]);
  const viewport = useSyncExternalStore(subscribeViewport, () => window.innerWidth, () => 1920);
  const frame = data.series.find((item) => item.length > 0);
  const fields = useMemo(() => frame?.fields.filter((field) => !hidden(field)) ?? [], [frame]);
  const displayFrame = useMemo(() => frame ? {
    ...frame,
    fields: fields.map((field) => ({
      ...field,
      config: { ...field.config, displayName: label(field) },
      state: { ...field.state, displayName: label(field) },
    })),
  } : undefined, [frame, fields]);

  const rowOrder = useMemo(() => orderedRows(frame, options.sortBy), [frame, options.sortBy]);
  const currentPage = Math.min(page, Math.max(0, rowOrder.length - 1));
  const row = rowOrder[currentPage] ?? 0;
  const isRuns = options.viewMode === 'runs';
  // The docked menu can constrain a desktop panel below the readable ten-column width.
  const isCompact = viewport < 1024 || (isRuns && (bounds?.width ?? width) < 1280);
  const isPaged = isRuns || options.viewMode === 'rows';

  // Supported Grafana versions expose query details through errors. A failed
  // request remains unavailable even when no details accompany its state.
  const status = queryStatus(data);
  if (status !== null) { return status; }
  if (!frame || fields.length === 0) {
    return <div className={shell}>UNKNOWN · No matching data</div>;
  }
  if (isRuns && !frame.fields.find((field) => field.name === 'run_id')?.values.some((value) => typeof value === 'string' && value !== '' && value !== '-')) {
    const validEmpty = frame.fields.find((field) => label(field) === 'Pipeline')?.values[0] === 'VALID EMPTY';
    return <div className={shell}>{validEmpty ? 'VALID EMPTY · No matching launches' : 'UNKNOWN · No run identity'}</div>;
  }
  // Explicit compact summaries may use metadata hidden from the wide table.
  const summaryFields = options.compactFields
    ? options.compactFields.map((name) => frame.fields.find((field) => label(field) === name)).filter((field): field is Field => Boolean(field))
    : fields;
  if (isCompact && options.compactFields && summaryFields.length !== options.compactFields.length) {
    return <div className={shell}>UNKNOWN · Required fields unavailable</div>;
  }

  const detailFields = frame.fields.filter((field) =>
    fields.includes(field) || ['run_id', 'pipeline', 'run_type', 'workflow_scope'].includes(field.name)
  );


  return (
    <div ref={setHost} className={isCompact ? `${shell} ${compact}` : nativeShell} data-bioetl-adaptive-table={isCompact ? 'compact' : 'wide'}>
      {isCompact ? (
        <CompactRows fields={summaryFields} row={row} isRuns={isRuns} isPaged={isPaged}
          title={props.title} currentPage={currentPage} rowCount={rowOrder.length}
          onPageChange={setPage} onDetails={setDetailRow} />
      ) : (
        <Table
          data={displayFrame as DataFrame}
          // PanelProps include the host border. Size the grid from the actual
          // content box, retaining its one-pixel border on each side.
          width={Math.max(0, (bounds?.width ?? width) - 2)}
          height={Math.max(0, (bounds?.height ?? height) - 2)}
          fieldConfig={fieldConfig}
          enablePagination={isPaged || options.enablePagination === true || options.footer?.enablePagination === true}
          cellHeight={options.cellHeight}
          noHeader={options.showHeader === false}
          sortBy={options.sortBy}
          noPanelPadding
          contentAwareWidthsEnabled
          preventHorizontalOverflow
          timeRange={timeRange}
        />
      )}
      <RunDetails fields={detailFields} row={detailRow} isRuns={isRuns} onDismiss={() => setDetailRow(null)} />
    </div>
  );
};

export const AdaptiveTable: React.FC<PanelProps<AdaptiveTableOptions>> = (props) => {
  const scope = props.replaceVariables('${workflow}|${pipeline}|${run_type}|${run_id}');
  const frame = props.data.series.find((item) => item.length > 0);
  const identities = frame?.fields.find((field) => field.name === 'run_id')?.values.join('|') ?? '';
  // A new scope or request state cannot retain an open detail from an old run.
  return <AdaptiveTableView key={`${scope}|${identities}|${props.data.state}`} {...props} />;
};
