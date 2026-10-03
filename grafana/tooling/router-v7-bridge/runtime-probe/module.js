/* Acceptance-only plugin. All router and React code comes from the running host. */
define(['react', 'react-dom/client', '@grafana/data', 'react-router'], function (React, ReactDOM, data, router) {
  'use strict';
  const vectors = ['//example.invalid', '\\\\example.invalid', '/\\example.invalid', '\\/example.invalid'];
  function Panel() {
    const [receipt, setReceipt] = React.useState(null);
    async function run() {
      const results = [];
      const check = (name, condition) => {
        results.push({ name, pass: Boolean(condition) });
        if (!condition) throw new Error(name);
      };
      const origin = window.location.origin;
      const savedHydration = window.__staticRouterHydrationData;
      const savedProbe = window.BioETLHarmlessProbe;
      let hydrationRouter;
      let node;
      let root;
      try {
        check('host exports patched bridge', typeof router.InternalLink === 'object' && typeof router.createBrowserRouter === 'function');
        node = document.createElement('div');
        document.body.appendChild(node);
        root = ReactDOM.createRoot(node);
        let navigate, location;
        function Observe() {
          navigate = router.useNavigate();
          location = router.useLocation();
          return React.createElement(React.Fragment, null,
            ...vectors.map((to, index) => React.createElement(router.InternalLink, { to, key: index }, to)));
        }
        root.render(React.createElement(router.MemoryRouter, { initialEntries: ['/home'] }, React.createElement(Observe)));
        for (let attempt = 0; attempt < 100 && !navigate; attempt++) await new Promise((resolve) => setTimeout(resolve, 20));
        check('host router fixture mounted', typeof navigate === 'function');
        for (const [index, to] of vectors.entries()) {
          const resolved = router.resolvePath(to, '/home').pathname;
          check('resolvePath origin: ' + JSON.stringify(to), new URL(resolved, window.location.href).origin === origin);
          const anchor = node.querySelectorAll('a')[index];
          check('InternalLink origin: ' + JSON.stringify(to), anchor && new URL(anchor.href).origin === origin);
          let rejected = false;
          try { navigate(to); } catch (error) { rejected = /External navigation is not allowed/.test(error.message); }
          await new Promise((resolve) => setTimeout(resolve, 30));
          check('useNavigate rejects: ' + JSON.stringify(to), rejected && location.pathname === '/home');
        }
        for (const to of ['/detail?run=42#panel', '/%2f%2fexample.invalid', '/%5cexample.invalid']) {
          navigate(to);
          await new Promise((resolve) => setTimeout(resolve, 30));
          const expected = new URL(to, origin);
          check('internal/encoded navigation: ' + to,
            location.pathname === expected.pathname && location.search === expected.search &&
            location.hash === expected.hash && window.location.origin === origin);
        }
        for (const subtype of ['BioETLHarmlessProbe', 'constructor', '__proto__', 'TypeError']) {
          let calls = 0;
          window.BioETLHarmlessProbe = function () { calls++; };
          window.__staticRouterHydrationData = {
            loaderData: {}, errors: { root: { __type: 'Error', __subType: subtype, message: 'local acceptance fixture' } },
          };
          hydrationRouter = router.createBrowserRouter([{ id: 'root', path: '*', element: null }], { window });
          check('hydration ignores arbitrary constructor: ' + subtype, calls === 0 && hydrationRouter.state.errors.root instanceof Error);
          hydrationRouter.dispose();
          hydrationRouter = null;
        }
        check('browser remains on host origin', window.location.origin === origin);
        setReceipt({ status: 'PASS', origin, results, dependency: 'Grafana shared react-router external; no bundled router copy' });
      } catch (error) {
        setReceipt({ status: 'FAIL', origin, results, error: error.message });
      } finally {
        hydrationRouter?.dispose();
        root?.unmount();
        node?.remove();
        if (savedHydration === undefined) delete window.__staticRouterHydrationData;
        else window.__staticRouterHydrationData = savedHydration;
        if (savedProbe === undefined) delete window.BioETLHarmlessProbe;
        else window.BioETLHarmlessProbe = savedProbe;
      }
    }
    return React.createElement('div', null,
      React.createElement('button', { onClick: run, type: 'button' }, 'Run host security acceptance'),
      React.createElement('pre', { 'data-testid': 'host-security-receipt', style: { whiteSpace: 'pre-wrap' } }, JSON.stringify(receipt, null, 2)));
  }
  return { plugin: new data.PanelPlugin(Panel) };
});
