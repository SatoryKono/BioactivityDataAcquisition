import type { SelectorShellOptions } from './types';
import type { TableCellHeight } from '@grafana/schema';

export interface AdaptiveTableOptions extends SelectorShellOptions {
  viewMode?: 'selectors' | 'runs' | 'record' | 'rows';
  showHeader?: boolean;
  cellHeight?: TableCellHeight;
  enablePagination?: boolean;
  footer?: { enablePagination?: boolean };
  compactFields?: string[];
  sortBy?: Array<{ displayName: string; desc: boolean }>;
}
