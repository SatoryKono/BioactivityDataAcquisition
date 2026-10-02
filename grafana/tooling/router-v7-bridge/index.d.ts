import type { ForwardRefExoticComponent, ReactElement, ReactNode, RefAttributes } from 'react';
import type { RouteProps } from 'react-router-dom';
import type { LinkProps } from 'react-router-v7';

export * from 'react-router-v7';
export declare function CompatRouter(props: { children?: ReactNode }): ReactElement;
export declare function CompatRoute(props: RouteProps): ReactElement;
export declare const InternalLink: ForwardRefExoticComponent<LinkProps & RefAttributes<HTMLAnchorElement>>;
