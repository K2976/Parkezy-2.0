"""Prometheus metrics (System Design Interview ch. 20: pull model, scraped by Prometheus/Grafana).

Per-process registry by default. With several uvicorn workers set PROMETHEUS_MULTIPROC_DIR so
all workers share counters (prometheus_client multiprocess mode).
"""

import os

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

REQUESTS = Counter("parkezy_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram(
    "parkezy_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
OUTBOX_PENDING = Gauge("parkezy_outbox_pending", "Outbox events waiting to be delivered", multiprocess_mode="max")
OUTBOX_DEAD = Gauge("parkezy_outbox_dead_letters", "Outbox events that exhausted retries", multiprocess_mode="max")


def observe(method: str, route: str, status: int, seconds: float) -> None:
    REQUESTS.labels(method, route, str(status)).inc()
    LATENCY.labels(method, route).observe(seconds)


def render() -> tuple[bytes, str]:
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return generate_latest(registry), CONTENT_TYPE_LATEST
    return generate_latest(), CONTENT_TYPE_LATEST
