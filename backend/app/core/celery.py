"""
Celery Configuration for Agentic BI Platform

This is a minimal celery configuration for the development environment.
Full implementation will be added in PR#2A (Core Integration POCs).
"""

import os
from celery import Celery

# Get Redis URL from environment
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Create Celery app
celery_app = Celery(
    "agentic_bi",
    broker=redis_url,
    backend=redis_url,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Auto-discover tasks from all registered apps
# This will be expanded in future PRs when we add task modules
celery_app.autodiscover_tasks(["app.tasks"])


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing celery connectivity"""
    return f"Request: {self.request!r}"
