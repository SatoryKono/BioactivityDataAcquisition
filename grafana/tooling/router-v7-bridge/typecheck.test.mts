import type { ComponentProps } from 'react';
import { CompatRoute, CompatRouter, InternalLink, Link, Routes, Route, useNavigate, useLocation, useParams, useSearchParams } from '@bioetl/grafana-router-v7-bridge';
import type { Params } from '@bioetl/grafana-router-v7-bridge';
const route: ComponentProps<typeof CompatRoute> = { path: ['/detail/:id', '/alternate/:id'], exact: true };
const internal: ComponentProps<typeof InternalLink> = { to: '/detail?run=42#panel' };
const params: Params = { id: '42' };
void [route, internal, params, CompatRouter, Link, Routes, Route, useNavigate, useLocation, useParams, useSearchParams];
