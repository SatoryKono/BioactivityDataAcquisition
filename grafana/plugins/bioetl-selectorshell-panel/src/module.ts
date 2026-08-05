import { PanelPlugin } from '@grafana/data';

import { SimplePanel } from './components/SimplePanel';
import { defaultOptions, SelectorShellOptions } from './types';

export const plugin = new PanelPlugin<SelectorShellOptions>(SimplePanel)
  .setNoPadding()
  .setPanelOptions((builder) => {
    return builder
      .addTextInput({
        path: 'selectorContextPath',
        name: 'Selector context path',
        description: 'Local HTTP endpoint used to resolve authoritative workflow/pipeline/run_type for an exact run_id.',
        defaultValue: defaultOptions.selectorContextPath,
      })
      .addBooleanSwitch({
        path: 'autoApplyExactRunContext',
        name: 'Auto-apply exact run context',
        description:
          'When enabled, the panel writes resolved workflow/pipeline/run_type back into visible dashboard variables via locationService.partial().',
        defaultValue: defaultOptions.autoApplyExactRunContext,
      })
      .addBooleanSwitch({
        path: 'autoApplyLastRunDefaults',
        name: 'Auto-apply last-run defaults',
        description:
          'When enabled and the shell is unset (All/unknown/-), apply coherent last-run defaults from selector-context, with run_type fallback backfill.',
        defaultValue: defaultOptions.autoApplyLastRunDefaults,
      })
      .addBooleanSwitch({
        path: 'showDebugDetails',
        name: 'Show debug payload',
        description: 'Render the raw selector-context payload for debugging.',
        defaultValue: defaultOptions.showDebugDetails,
      });
  });
