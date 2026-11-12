import React from 'react';
import { PanelPlugin, type PanelProps } from '@grafana/data';
import type { TableFieldOptions } from '@grafana/ui';
import { AdaptiveTable } from './components/AdaptiveTable';
import { SimplePanel } from './components/SimplePanel';
import type { AdaptiveTableOptions } from './adaptive-types';

// Separate managed entrypoint: the previously accepted selector-shell build
// and its immutable host image retain their original inputs and behaviour.
const ManagedPanel: React.FC<PanelProps<AdaptiveTableOptions>> = (props) =>
  React.createElement(props.options.viewMode && props.options.viewMode !== 'selectors' ? AdaptiveTable : SimplePanel, props);

const managedEditor = () => React.createElement('span', null, 'Provided by dashboard provisioning.');

export const plugin = new PanelPlugin<AdaptiveTableOptions, TableFieldOptions>(ManagedPanel)
  .useFieldConfig({
    useCustomConfig: (builder) => {
      builder
        .addNumberInput({ path: 'width', name: 'Column width' })
        .addNumberInput({ path: 'minWidth', name: 'Minimum column width' })
        .addBooleanSwitch({ path: 'hidden', name: 'Hide column', defaultValue: false })
        .addBooleanSwitch({ path: 'inspect', name: 'Inspect cell', defaultValue: false })
        .addBooleanSwitch({ path: 'filterable', name: 'Filter column', defaultValue: false });
      // Retain the native table's object-valued configuration in this managed,
      // read-only profile. Unregistered custom overrides are dropped by Grafana.
      for (const key of ['cellOptions', 'hideFrom', 'wrapText', 'align', 'tooltip.field']) {
        builder.addCustomEditor({
          id: key, path: key, name: key,
          editor: managedEditor, override: managedEditor,
          process: (value: unknown) => value,
          shouldApply: () => true,
        });
      }
    },
  })
  .setNoPadding()
  .setPanelOptions((builder) => builder.addSelect({
    path: 'viewMode',
    name: 'Panel content',
    defaultValue: 'selectors',
    settings: {
      options: [
        { label: 'Selector shell', value: 'selectors' },
        { label: 'Responsive run catalog', value: 'runs' },
        { label: 'Responsive record', value: 'record' },
        { label: 'Responsive evidence rows', value: 'rows' },
      ],
    },
  }));
