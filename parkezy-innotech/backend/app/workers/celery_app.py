import logging

from celery import Celery

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.workers import jobs, runtime

settings = get_settings()
configure_logging(settings.log_level)
log = logging.getLogger(__name__)

TASK_PREFIX = "parkezy."

celery = Celery("parkezy", broker=settings.broker_url)
celery.conf.update(
    task_acks_late=True,  # a crashed worker's task is redelivered; jobs are idempotent
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=True,
    broker_connection_retry_on_startup=True,
    broker_pool_limit=settings.celery_broker_pool_limit,
    broker_transport_options={
        "socket_timeout": settings.redis_socket_timeout_seconds,
        "socket_connect_timeout": settings.redis_socket_timeout_seconds,
        "health_check_interval": settings.redis_health_check_seconds,
    },
    # The API publishes "wake up" nudges inline; a dead broker must not stall requests. Beat's
    # periodic sweeps pick up anything a failed nudge missed (transactional outbox).
    task_publish_retry_policy={"max_retries": 2, "interval_start": 0, "interval_step": 0.2, "interval_max": 0.5},
    timezone="UTC",
    beat_schedule={
        "outbox-sweep": {"task": f"{TASK_PREFIX}process_outbox", "schedule": float(settings.outbox_sweep_seconds)},
        "maintenance": {"task": f"{TASK_PREFIX}maintenance", "schedule": float(settings.maintenance_sweep_seconds)},
        "reconcile-payments": {
            "task": f"{TASK_PREFIX}reconcile_payments",
            "schedule": float(settings.payment_reconcile_interval_seconds),
        },
        "cleanup": {"task": f"{TASK_PREFIX}cleanup", "schedule": float(settings.cleanup_interval_hours * 3600)},
    },
)


class CeleryJobQueue:
    def enqueue(self, task: str, *args: object, countdown_seconds: int | None = None) -> None:
        celery.send_task(f"{TASK_PREFIX}{task}", args=list(args), countdown=countdown_seconds)


@celery.task(name=f"{TASK_PREFIX}process_outbox")
def process_outbox() -> int:
    return runtime.run(jobs.process_outbox)


@celery.task(name=f"{TASK_PREFIX}maintenance")
def maintenance() -> dict:
    return runtime.run(jobs.maintenance)


@celery.task(name=f"{TASK_PREFIX}reconcile_payments")
def reconcile_payments() -> dict:
    return runtime.run(jobs.reconcile_payments)


@celery.task(name=f"{TASK_PREFIX}cleanup")
def cleanup() -> dict:
    return runtime.run(jobs.cleanup)


@celery.task(
    name=f"{TASK_PREFIX}refund_payment",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,
    max_retries=10,
)
def refund_payment(payment_id: str, amount: str) -> None:
    runtime.run(lambda c: jobs.refund_payment(c, payment_id, amount))
