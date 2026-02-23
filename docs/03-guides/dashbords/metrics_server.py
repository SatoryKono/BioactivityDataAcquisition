#!/usr/bin/env python3
"""BioETL-compatible Prometheus metrics server with sample data.

Generates synthetic metrics matching the production label schema defined in
src/bioetl/infrastructure/observability/metrics.py.
"""

import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY

# Metrics aligned with production schema (metrics.py)
RECORDS_PROCESSED = Counter(
    'bioetl_records_processed_total',
    'Total records processed',
    ['pipeline', 'stage', 'run_type'],  # matches production labels
)

PIPELINE_DURATION = Histogram(
    'bioetl_pipeline_duration_seconds',
    'Pipeline duration in seconds',
    ['pipeline', 'stage', 'status', 'run_type'],
)

ERRORS_TOTAL = Counter(
    'bioetl_errors_total',
    'Total errors',
    ['pipeline', 'stage', 'error_code'],
)

DQ_QUARANTINED = Counter(
    'bioetl_dq_records_quarantined_total',
    'Quarantined records',
    ['pipeline', 'error_type', 'run_type'],
)

INFRASTRUCTURE_VALIDATED = Gauge(
    'bioetl_infrastructure_validated',
    'Infrastructure validation status',
    ['pipeline', 'run_id'],
)

HEALTH_CHECK_PASSED = Gauge(
    'bioetl_pipeline_health_check_passed',
    'Health check status (1=passed, 0=failed)',
    ['pipeline', 'component'],
)

HEALTH_CHECK_DURATION = Histogram(
    'bioetl_health_check_duration_seconds',
    'Health check duration',
    ['pipeline'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics endpoint."""

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/metrics':
            self._generate_synthetic_metrics()

            metrics_output = generate_latest(REGISTRY)

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; version=0.0.4; charset=utf-8')
            self.send_header('Content-Length', len(metrics_output))
            self.end_headers()
            self.wfile.write(metrics_output)
        elif self.path == '/health':
            response = b'{"status":"healthy"}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            self.wfile.write(response)
        else:
            self.send_response(404)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Found')

    def _generate_synthetic_metrics(self):
        """Generate synthetic BioETL metrics matching production schema."""
        pipelines = ['chembl_molecule', 'chembl_mechanism', 'pubchem_bioassay', 'uniprot_protein']
        run_id = f'run-{int(time.time() / 3600)}'
        stages = ['bronze', 'silver', 'gold', 'quarantined']
        run_type = 'incremental'

        for pipeline in pipelines:
            # Infrastructure validation
            INFRASTRUCTURE_VALIDATED.labels(pipeline=pipeline, run_id=run_id).set(1)

            # Health checks
            for component in ['data_source', 'storage', 'transform']:
                HEALTH_CHECK_PASSED.labels(pipeline=pipeline, component=component).set(
                    1 if random.random() > 0.05 else 0
                )

            HEALTH_CHECK_DURATION.labels(pipeline=pipeline).observe(random.uniform(0.01, 2.0))

            for stage in stages:
                if stage == 'quarantined':
                    records = random.randint(0, 20)
                else:
                    records = random.randint(100, 1000)

                RECORDS_PROCESSED.labels(
                    pipeline=pipeline,
                    stage=stage,
                    run_type=run_type,
                ).inc(records)

                PIPELINE_DURATION.labels(
                    pipeline=pipeline,
                    stage=stage,
                    status='success',
                    run_type=run_type,
                ).observe(random.uniform(0.5, 30.0))

            # Errors (occasional)
            if random.random() > 0.8:
                ERRORS_TOTAL.labels(
                    pipeline=pipeline,
                    stage='silver',
                    error_code='validation_error',
                ).inc(random.randint(1, 5))

            # DQ quarantine details
            DQ_QUARANTINED.labels(
                pipeline=pipeline,
                error_type='schema_violation',
                run_type=run_type,
            ).inc(random.randint(0, 10))

    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        return


if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), MetricsHandler)
    print('BioETL Metrics server running on http://0.0.0.0:8000/metrics', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...', flush=True)
        server.shutdown()
