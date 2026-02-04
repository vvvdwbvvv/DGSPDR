from __future__ import annotations

import os
from pathlib import Path
import subprocess

from prefect import flow, task
from prefect.logging import get_run_logger
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = "courses_complete_it"
DEFAULT_WORK_POOL = os.getenv("PREFECT_WORK_POOL", "default")
DEFAULT_WORK_QUEUE = os.getenv("PREFECT_WORK_QUEUE")


@task
def run_make_target(target: str, dry_run: bool = False) -> None:
    logger = get_run_logger()
    logger.info("Running make target: %s", target)
    command = ["make", target]
    if dry_run:
        command.insert(1, "--dry-run")
        logger.info("Dry run enabled; skipping scraper execution.")
    subprocess.run(command, cwd=REPO_ROOT, check=True)


@flow(name="daily-scrape")
def daily_scrape(target: str = DEFAULT_TARGET, dry_run: bool = False) -> None:
    run_make_target(target, dry_run=dry_run)


def build_daily_deployment(
    cron: str = "0 2 * * *",
    timezone: str = "UTC",
    target: str = DEFAULT_TARGET,
    work_pool_name: str = DEFAULT_WORK_POOL,
    work_queue_name: str | None = DEFAULT_WORK_QUEUE,
) -> Deployment:
    return Deployment.build_from_flow(
        flow=daily_scrape,
        name="daily-scrape",
        schedule=CronSchedule(cron=cron, timezone=timezone),
        parameters={"target": target},
        work_pool_name=work_pool_name,
        work_queue_name=work_queue_name,
    )


if __name__ == "__main__":
    deployment = build_daily_deployment()
    deployment.apply()
