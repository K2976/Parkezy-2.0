"""Prometheus metrics (System Design Interview ch. 20: pull model, scraped by Prometheus/Grafana).

Per-process registry by default. With several uvicorn workers set PROMETHEUS_MULTIPROC_DIR so
all workers share counters (prometheus_client multiprocess mode).
"""

import os

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
    multiprocess,
)
from prometheus_client.core import GaugeMetricFamily

REQUESTS = Counter("parkezy_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram(
    "parkezy_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)


class _QueueCollector:
    """Outbox gauges read fresh from the database on every scrape (see /metrics).

    Deliberately NOT prometheus_client Gauges: in multiprocess mode each worker writes its last
    value to a file, and files of workers that died (crash, restart) are never cleaned up without a
    process-manager hook, so a dead worker's stale number would win "max" forever."""

    def __init__(self, stats: dict[str, int]) -> None:
        self._stats = stats

    def collect(self):
        pending, dead = self._stats["pending"], self._stats["dead"]
        yield GaugeMetricFamily("parkezy_outbox_pending", "Outbox events waiting to be delivered", pending)
        yield GaugeMetricFamily("parkezy_outbox_dead_letters", "Outbox events that exhausted retries", dead)


def observe(method: str, route: str, status: int, seconds: float) -> None:
    REQUESTS.labels(method, route, str(status)).inc()
    LATENCY.labels(method, route).observe(seconds)


def render(queue_stats: dict[str, int]) -> tuple[bytes, str]:
    registry = CollectorRegistry()
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        multiprocess.MultiProcessCollector(registry)  # request metrics summed across workers
    else:
        registry.register(_ProcessMetrics())
    registry.register(_QueueCollector(queue_stats))
    return generate_latest(registry), CONTENT_TYPE_LATEST


class _ProcessMetrics:
    """Single-process mode: expose the default registry (request metrics, process/GC stats)."""

    def collect(self):
        yield from REGISTRY.collect()
