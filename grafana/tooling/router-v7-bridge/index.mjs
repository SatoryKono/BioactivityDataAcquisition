import React, { useCallback, useSyncExternalStore } from 'react';
import { useHistory, Route as LegacyRoute } from 'react-router-dom';
import { Router, Routes, Route, Link, useResolvedPath } from 'react-router-v7';

export * from 'react-router-v7';

/** Explicit internal-link boundary; native Link still supports external URLs. */
export const InternalLink = React.forwardRef(function InternalLink({ to, ...props }, ref) {
  const pathname = typeof to === 'string' ? to : to?.pathname;
  if (pathname && /^[a-z][a-z0-9+.-]*:/i.test(pathname)) {
    throw new TypeError('InternalLink only accepts route paths');
  }
  const resolved = useResolvedPath(to);
  return React.createElement(Link, { ...props, to: resolved, ref });
});

/** Candidate bridge: both routers share legacy history, not private v6 APIs. */
export function CompatRouter({ children }) {
  const history = useHistory();
  const subscribe = useCallback((notify) => history.listen(notify), [history]);
  const snapshot = useCallback(() => history.location, [history]);
  const location = useSyncExternalStore(subscribe, snapshot, snapshot);

  return React.createElement(
    Router,
    { location, navigationType: history.action, navigator: history },
    React.createElement(Routes, null, React.createElement(Route, { path: '*', element: children }))
  );
}

/** Preserve v5 Route rendering while supplying a matching v7 Route context. */
export function CompatRoute(props) {
  const paths = props.path == null ? [null] : Array.isArray(props.path) ? props.path : [props.path];
  return React.createElement(
    Routes,
    { location: props.location },
    ...paths.map((path, index) => {
      const routePath = path == null ? '*' : props.exact ? path : `${path.replace(/\/+$/, '')}/*`;
      return React.createElement(Route, {
        key: index,
        path: routePath,
        element: React.createElement(LegacyRoute, props),
      });
    })
  );
}
