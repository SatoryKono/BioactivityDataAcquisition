import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';
import { JSDOM } from 'jsdom';

const dom = new JSDOM('<body></body>', { url: 'http://127.0.0.1:3000/' });
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const { default: React } = await import('react');
const ReactDOM = await import('react-dom/client');
const bridge = await import('../index.mjs');
const source = readFileSync(new URL('./module.js', import.meta.url), 'utf8');
const pause = () => new Promise((resolve) => setTimeout(resolve, 20));

async function runProbe(code, router) {
  let Panel;
  vm.runInNewContext(code, {
    window, document, URL, Error, setTimeout,
    define: (_, factory) => factory(React, ReactDOM, {
      PanelPlugin: class { constructor(component) { Panel = component; } },
    }, router),
  });
  const node = document.createElement('div');
  document.body.appendChild(node);
  const root = ReactDOM.createRoot(node);
  try {
    root.render(React.createElement(Panel));
    for (let attempt = 0; attempt < 100 && !node.querySelector('button'); attempt++) await pause();
    assert.ok(node.querySelector('button'), 'Probe mounted');
    node.querySelector('button').click();
    for (let attempt = 0; attempt < 500; attempt++) {
      const receipt = JSON.parse(node.querySelector('pre').textContent);
      if (receipt) return receipt;
      await pause();
    }
    throw new Error('Probe did not finish');
  } finally {
    root.unmount();
    node.remove();
  }
}

const transitionThenThrow = {
  ...bridge,
  useNavigate() {
    const navigate = bridge.useNavigate();
    return (to) => {
      if (to.includes('example.invalid') && !to.startsWith('/%')) {
        navigate('/unexpected');
        throw new Error('External navigation is not allowed');
      }
      return navigate(to);
    };
  },
};

test('probe accepts the bridge without an external transition', async () => {
  const receipt = await runProbe(source, bridge);
  assert.equal(receipt.status, 'PASS', JSON.stringify(receipt));
});

test('probe detects a transition committed after navigation throws', async () => {
  const receipt = await runProbe(source, transitionThenThrow);
  assert.equal(receipt.status, 'FAIL');
  assert.match(receipt.error, /^useNavigate rejects:/);
});
