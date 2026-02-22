#!/usr/bin/env python3
"""BioETL-compatible Prometheus metrics server with sample data."""

import sys
import random
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY, Info
from prometheus_client.core import CollectorRegistry

# Create custom metrics matching BioETL schema
RECORDS_PROCESSED = Counter(
    'bioetl_records_processed_total',
    'Total records processed',
    ['pipeline', 'run_id', 'stage', 'status']
)

PROCESSING_TIME = Histogram(
    'bioetl_processing_duration_seconds',
    'Processing duration',
    ['pipeline', 'stage']
)

ERROR_RATE = Gauge(
    'bioetl_error_rate',
    'Error rate',
    ['pipeline', 'stage']
)

# Метрика времени запуска
RUN_INFO = Info(
    'bioetl_run',
    'BioETL run information',
    ['run_id', 'pipeline', 'start_time', 'timestamp']
)

# Gauge для времени запуска (Unix timestamp)
RUN_START_TIME = Gauge(
    'bioetl_run_start_timestamp',
    'Run start time (Unix timestamp)',
    ['run_id', 'pipeline']
)

class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics endpoint."""
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/metrics':
            # Generate synthetic data
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
        """Generate synthetic BioETL metrics."""
        pipelines = ['uniprot', 'pubmed', 'pubchem', 'chembl']
        run_id = f'run-{int(time.time() / 3600)}'  # Same run_id per hour
        stages = ['bronze', 'silver', 'gold']
        
        # Текущее время (Unix timestamp)
        current_timestamp = int(time.time())
        current_time_str = datetime.fromtimestamp(current_timestamp).isoformat()
        
        for pipeline in pipelines:
            # Установить информацию о запуске
            RUN_INFO.labels(
                run_id=run_id,
                pipeline=pipeline,
                start_time=current_time_str,
                timestamp=str(current_timestamp)
            ).info({
                'run_id': run_id,
                'pipeline': pipeline,
                'start_time': current_time_str,
                'timestamp': str(current_timestamp)
            })
            
            # Установить Gauge с временем запуска
            RUN_START_TIME.labels(
                run_id=run_id,
                pipeline=pipeline
            ).set(current_timestamp)
            
            for stage in stages:
                # Increment counters with realistic numbers
                records = random.randint(100, 1000)
                RECORDS_PROCESSED.labels(
                    pipeline=pipeline,
                    run_id=run_id,
                    stage=stage,
                    status='success'
                ).inc(records)
                
                # Small error rate
                if random.random() > 0.95:
                    RECORDS_PROCESSED.labels(
                        pipeline=pipeline,
                        run_id=run_id,
                        stage=stage,
                        status='error'
                    ).inc(random.randint(1, 10))
                
                # Processing time
                PROCESSING_TIME.labels(
                    pipeline=pipeline,
                    stage=stage
                ).observe(random.uniform(0.5, 5.0))
                
                # Error rate
                ERROR_RATE.labels(
                    pipeline=pipeline,
                    stage=stage
                ).set(random.uniform(0, 0.05))
    
    def log_message(self, format, *args):
        """Suppress HTTP server logs."""
        return

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8000), MetricsHandler)
    print('BioETL Metrics server running on http://0.0.0.0:8000/metrics', flush=True)
    print('Available metrics:', flush=True)
    print('  - bioetl_records_processed_total', flush=True)
    print('  - bioetl_processing_duration_seconds', flush=True)
    print('  - bioetl_error_rate', flush=True)
    print('  - bioetl_run (run info with start_time)', flush=True)
    print('  - bioetl_run_start_timestamp (Unix timestamp)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down...', flush=True)
        server.shutdown()
