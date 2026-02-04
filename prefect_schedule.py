from __future__ import annotations

import subprocess
from pathlib import Path

from prefect import flow, task
from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule


@task
def run_scraper(make_target: str) -> None:
    repo_root = Path(__file__).resolve().parent
    subprocess.run(["make", make_target], check=True, cwd=repo_root)


@flow(name="dgspdr-daily-scraper")
def daily_scraper(make_target: str = "courses") -> None:
    run_scraper(make_target)


def build_daily_deployment(make_target: str = "courses") -> None:
    deployment = Deployment.build_from_flow(
        flow=daily_scraper,
        name="daily-scraper",
        schedule=CronSchedule(cron="0 0 * * *", timezone="UTC"),
        parameters={"make_target": make_target},
        description="Daily Prefect deployment for DGSPDR scraper.",
    )
    deployment.apply()


if __name__ == "__main__":
    build_daily_deployment()
