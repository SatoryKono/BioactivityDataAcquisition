import type { SelectorShellOptions } from './types';
import type { DataQuery, TableCellHeight } from '@grafana/schema';
import type { DataTransformerConfig } from '@grafana/data';

export interface AdaptiveTableOptions extends SelectorShellOptions {
  viewMode?: 'selectors' | 'runs' | 'record' | 'rows' | 'current';
  currentView?: {
    pluginId: 'stat' | 'table' | 'timeseries';
    queries: DataQuery[];
    transformations: DataTransformerConfig[];
    options: Record<string, unknown>;
    compactFields?: string[];
  };
  showHeader?: boolean;
  cellHeight?: TableCellHeight;
  enablePagination?: boolean;
  footer?: { enablePagination?: boolean };
  compactFields?: string[];
  sortBy?: Array<{ displayName: string; desc: boolean }>;
}
