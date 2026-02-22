#!/usr/bin/env python3
"""Simple Prometheus metrics server for BioETL."""

import asyncio
import logging
from pathlib import Path
from sys import path as sys_path

# Add src to path for imports
sys_path.insert(0, str(Path(__file__).parent / "src"))

from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.observability import start_metrics_server
from bioetl.composition.bootstrap.runtime import bootstrap_metrics_port

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

async def main():
    """Run metrics server."""
    try:
        # Load settings
        settings = Settings()
        
        # Bootstrap metrics
        metrics_port = bootstrap_metrics_port(settings)
        logger.info(f"Metrics initialized: {type(metrics_port).__name__}")
        
        # Start metrics server
        logger.info(f"Starting metrics server on {settings.metrics_addr}:{settings.metrics_port}")
        success = await asyncio.to_thread(
            lambda: start_metrics_server(
                port=settings.metrics_port,
                addr=settings.metrics_addr,
                fail_fast=False,
            )
        )
        
        if success:
            logger.info(f"Metrics server running on http://{settings.metrics_addr}:{settings.metrics_port}/metrics")
            # Keep running
            while True:
                await asyncio.sleep(1)
        else:
            logger.error("Failed to start metrics server")
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())
