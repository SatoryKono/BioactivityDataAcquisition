import assert from 'node:assert/strict';
import { test } from 'node:test';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<div id="root"></div>', { url: 'http://127.0.0.1:3000/' });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const { default: React, act } = await import('react');
const { createRoot } = await import('react-dom/client');
const { renderToString } = await import('react-dom/server');
const { default: legacy } = await import('react-router-dom');
const bridge = await import('./index.mjs');

async function mount(children, entries = ['/home']) {
  const node = document.createElement('div');
  document.body.appendChild(node);
  const root = createRoot(node);
  await act(async () => root.render(React.createElement(legacy.MemoryRouter, { initialEntries: entries }, children)));
  return { node, async dispose() { await act(async () => root.unmount()); node.remove(); } };
}

test('legacy history and v7 navigation share push, replace, search/hash, and back', async () => {
  let oldHistory;
  let navigate;
  let current;
  function Observe() {
    oldHistory = legacy.useHistory();
    navigate = bridge.useNavigate();
    current = bridge.useLocation();
    return React.createElement('span', null, current.pathname + current.search + current.hash);
  }
  const view = await mount(React.createElement(bridge.CompatRouter, null, React.createElement(Observe)));
  try {
    await act(async () => navigate('/detail?var-run_id=42#panel'));
    assert.equal(oldHistory.location.pathname, '/detail');
    assert.equal(view.node.textContent, '/detail?var-run_id=42#panel');
    assert.equal(oldHistory.action, 'PUSH');
    await act(async () => navigate('/replacement', { replace: true }));
    assert.equal(oldHistory.action, 'REPLACE');
    assert.equal(current.pathname, '/replacement');
    await act(async () => oldHistory.goBack());
    assert.equal(current.pathname, '/home');
    await act(async () => oldHistory.push('/legacy'));
    assert.equal(current.pathname, '/legacy');
  } finally { await view.dispose(); }
});

test('CompatRoute preserves v5 params and v7 params for nested and array paths', async () => {
  function Both() {
    return React.createElement('span', null, legacy.useParams().id + ':' + bridge.useParams().id);
  }
  const view = await mount(React.createElement(bridge.CompatRouter, null,
    React.createElement(bridge.CompatRoute, { path: ['/unused/:id', '/detail/:id'], component: Both })), ['/detail/42/child']);
  try { assert.equal(view.node.textContent, '42:42'); } finally { await view.dispose(); }
});

test('CompatRoute exact path does not render for an unmatched descendant', async () => {
  const view = await mount(React.createElement(bridge.CompatRouter, null,
    React.createElement(bridge.CompatRoute, { path: '/detail', exact: true, component: () => 'unexpected' })), ['/detail/child']);
  try { assert.equal(view.node.textContent, ''); } finally { await view.dispose(); }
});

test('legacy history subscription is removed when bridge unmounts', async () => {
  let active = 0;
  function Instrument() {
    const history = legacy.useHistory();
    const original = history.listen.bind(history);
    history.listen = (listener) => {
      active += 1;
      const stop = original(listener);
      return () => { active -= 1; stop(); };
    };
    return React.createElement(bridge.CompatRouter, null, 'ready');
  }
  const view = await mount(React.createElement(Instrument));
  try { assert.ok(active > 0); } finally { await view.dispose(); }
  assert.equal(active, 0);
});

test('mixed separator navigation paths preserve origin and normalize to internal paths', async () => {
  for (const to of ['//foo', '\\\\foo', '/\\foo', '\\/foo']) {
    const resolved = bridge.resolvePath(to, '/home').pathname;
    assert.equal(resolved, '/foo');
    assert.equal(new URL(resolved, window.location.href).origin, window.location.origin);
    const view = await mount(React.createElement(bridge.CompatRouter, null,
      React.createElement(bridge.InternalLink, { to }, 'open')));
    try {
      const anchor = view.node.querySelector('a');
      assert.equal(new URL(anchor.href).origin, window.location.origin);
    } finally { await view.dispose(); }
  }
});

test('InternalLink preserves query/hash and Link permits intentional external URLs', async () => {
  const view = await mount(React.createElement(bridge.CompatRouter, null,
    React.createElement(React.Fragment, null,
      React.createElement(bridge.InternalLink, { to: '/detail?run=42#panel' }, 'internal'),
      React.createElement(bridge.Link, { to: 'https://example.invalid/help' }, 'external'))));
  try {
    const [internal, external] = view.node.querySelectorAll('a');
    assert.equal(internal.getAttribute('href'), '/detail?run=42#panel');
    assert.equal(external.href, 'https://example.invalid/help');
  } finally { await view.dispose(); }
});

test('InternalLink rejects an explicit external scheme before rendering', () => {
  for (const to of ['https://example.invalid/', 'javascript:alert(1)', { pathname: 'https://example.invalid/' }]) {
    assert.throws(() => renderToString(React.createElement(legacy.MemoryRouter, null,
      React.createElement(bridge.CompatRouter, null,
        React.createElement(bridge.InternalLink, { to }, 'internal')))), /only accepts route paths/);
  }
});

test('hydration decoder never invokes an arbitrary constructor from window', () => {
  let calls = 0;
  window.BioETLHarmlessProbe = function () { calls += 1; };
  window.__staticRouterHydrationData = {
    loaderData: {},
    errors: { root: { __type: 'Error', __subType: 'BioETLHarmlessProbe', message: 'local probe' } },
  };
  let router;
  try {
    router = bridge.createBrowserRouter([{ id: 'root', path: '/', element: null }], { window });
    assert.equal(calls, 0);
    assert.ok(router.state.errors.root instanceof Error);
  } finally {
    router?.dispose();
    delete window.BioETLHarmlessProbe;
    delete window.__staticRouterHydrationData;
  }
});
