// Jest setup provided by Grafana scaffolding
import './.config/jest-setup';

// Scenes creates its lazy-layout observer on import; jsdom has no layout engine.
globalThis.IntersectionObserver = jest.fn(() => ({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
}));
