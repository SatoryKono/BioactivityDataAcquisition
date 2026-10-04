import { locationService } from '@grafana/runtime';
import { SceneFlexItem, SceneFlexLayout, VizPanel } from '@grafana/scenes';

import { WORKSPACE_ROUTES } from '../routes/registry';
import { buildWorkspaceScene } from './presentation';

// Use the real Node renderer in jsdom, which lacks browser MessageChannel.
jest.mock('react-dom/server', () => jest.requireActual('react-dom/server.node'));

describe('workspace fallback scope', () => {
  it('tracks exact-run changes and Back while active, then releases its location subscription', () => {
    locationService.push('/a/bioetl-scenes-app/run-explorer?var-pipeline=chembl_assay&var-run_id=first&from=now-12h&to=now&timezone=UTC');
    const scene = buildWorkspaceScene(WORKSPACE_ROUTES[0]);
    const layout = scene.state.body as SceneFlexLayout;
    const item = layout.state.children[0] as SceneFlexItem;
    const panel = item.state.body as VizPanel<{ content: string }>;
    const deactivate = scene.activate();
    try {
      expect(panel.state.options.content).toContain('var-run_id=first');
      expect(panel.state.options.content).toContain('var-pipeline=chembl_assay');
      locationService.partial({ 'var-run_id': 'second', from: 'now-24h', payload_hash: 'private' }, true);
      expect(panel.state.options.content).toContain('var-run_id=second');
      expect(panel.state.options.content).not.toContain('payload_hash');
      expect(panel.state.options.content).toContain('from=now-24h');
      expect(panel.state.options.content).toContain('timezone=UTC');
      locationService.push('/a/bioetl-scenes-app/run-explorer?var-run_id=later&from=now-48h');
      expect(panel.state.options.content).toContain('var-run_id=later');
      locationService.getHistory().goBack();
      expect(panel.state.options.content).toContain('var-run_id=second');
      expect(panel.state.options.content).toContain('from=now-24h');
      window.history.replaceState({}, '', '/a/bioetl-scenes-app/run-explorer?var-run_id=native&from=now-6h');
      window.dispatchEvent(new PopStateEvent('popstate'));
      expect(panel.state.options.content).toContain('var-run_id=native');
      expect(panel.state.options.content).toContain('from=now-6h');
    } finally {
      deactivate();
    }
    locationService.partial({ 'var-run_id': 'third' }, true);
    window.history.replaceState({}, '', '/a/bioetl-scenes-app/run-explorer?var-run_id=detached');
    window.dispatchEvent(new PopStateEvent('popstate'));
    expect(panel.state.options.content).toContain('var-run_id=native');
    locationService.replace('/');
  });
});
