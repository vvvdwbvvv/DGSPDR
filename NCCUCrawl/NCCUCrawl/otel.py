import json
import logging
import os
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from twisted.internet.threads import deferToThread
from scrapy import signals


# ---------- Otel setup ----------
def setup_otel(service_name: str = "scrapy-service") -> None:
    """
    Initialize OpenTelemetry tracing for Scrapy.
    If OTEL_EXPORTER_OTLP_ENDPOINT is set, use OTLP exporter; otherwise log to console.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
    except Exception as e:
        logging.getLogger(__name__).warning("OTel not available: %s", e)
        return

    # Avoid re-initialization if a TracerProvider already exists
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return

    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", service_name),
            "service.version": os.getenv("SERVICE_VERSION", "0.1.0"),
            "deployment.environment": os.getenv("DEPLOYMENT_ENV", "dev"),
            "host.name": socket.gethostname(),
        }
    )

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    else:
        exporter = ConsoleSpanExporter()

    provider.add_span_processor(BatchSpanProcessor(exporter))


# ---------- Discord webhook helper ----------
def _build_discord_payload(
    title: str,
    description: str,
    stats: Dict[str, Any],
    mentions: str = "",
    extra_fields: Optional[List[Dict[str, Any]]] = None,
    color: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Build a Discord webhook payload (embed style).
    Supports common Scrapy stats + optional extra fields.
    """

    def fmt_ts(ts: Any) -> str:
        if not ts:
            return "—"
        try:
            if isinstance(ts, (int, float)):
                return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
            if isinstance(ts, datetime):
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                return ts.isoformat()
            return str(ts)
        except Exception:
            return str(ts)

    lines: List[str] = []

    # Common keys to display
    common_keys = [
        "start_time",
        "finish_time",
        "elapsed_time_seconds",
        "item_scraped_count",
        "item_dropped_count",
        "downloader/request_count",
        "downloader/response_count",
        "log_count/ERROR",
        "log_count/CRITICAL",
        "httpcache/hit",
        "httpcache/miss",
    ]

    for k in common_keys:
        v = stats.get(k)
        if k in ("start_time", "finish_time"):
            v = fmt_ts(v)
        elif k == "elapsed_time_seconds" and v is not None:
            try:
                v = f"{float(v):.2f}s"
            except Exception:
                pass
        if v not in (None, 0, "", []):
            lines.append(f"• **{k}**: {v}")

    # Exception summary
    exc_stats = [
        (k, v)
        for k, v in stats.items()
        if isinstance(k, str) and k.startswith("downloader/exception_type_count/")
    ]
    if exc_stats:
        lines.append("**Exceptions:**")
        for k, v in sorted(exc_stats, key=lambda x: x[1], reverse=True)[:10]:
            lines.append(f"  - {k.split('/')[-1]}: {v}")

    if "offsite/domains" in stats:
        lines.append(f"• **offsite/domains**: {stats['offsite/domains']}")

    embed_description = "\n".join(lines) or "No notable stats."
    embed: Dict[str, Any] = {
        "title": title,
        "description": f"{description}\n\n{embed_description}",
        "type": "rich",
    }
    if color is not None:
        embed["color"] = color
    if extra_fields:
        embed["fields"] = extra_fields

    return {
        "content": (mentions.strip() if mentions else ""),
        "embeds": [embed],
    }


def send_discord_webhook(
    webhook_url: str, payload: Dict[str, Any], timeout: float = 10.0
) -> Dict[str, Any]:
    """Send webhook synchronously. Wrap with deferToThread to avoid blocking Scrapy's reactor."""
    resp = requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=timeout,
    )
    return {"status_code": resp.status_code, "text": resp.text}


# ---------- Scrapy extension ----------
class ObservabilityExtension:
    """
    Scrapy extension:
      - Initializes OpenTelemetry
      - Sends a Discord webhook when a spider finishes
    """

    def __init__(
        self, webhook_url: str, mentions: str, service_name: str, logger: logging.Logger
    ):
        self.webhook_url = webhook_url
        self.mentions = mentions
        self.service_name = service_name
        self.logger = logger

    @classmethod
    def from_crawler(cls, crawler):
        settings = crawler.settings

        service_name = (
            settings.get("OBS_SERVICE_NAME")
            or os.getenv("OTEL_SERVICE_NAME")
            or "scrapy-service"
        )
        setup_otel(service_name=service_name)

        webhook_url = settings.get("DISCORD_WEBHOOK_URL") or os.getenv(
            "DISCORD_WEBHOOK_URL"
        )
        mentions = settings.get(
            "OBS_WEBHOOK_MENTIONS", os.getenv("OBS_WEBHOOK_MENTIONS", "")
        )

        ext = cls(
            webhook_url=webhook_url or "",
            mentions=mentions or "",
            service_name=service_name,
            logger=logging.getLogger(__name__),
        )

        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_error, signal=signals.spider_error)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    # ---- signals ----
    def spider_opened(self, spider):
        self.logger.info(
            "ObservabilityExtension active for spider=%s (service=%s)",
            spider.name,
            self.service_name,
        )

    def spider_error(self, failure, response, spider):
        """Record extra stats on spider errors."""
        try:
            stats = spider.crawler.stats
            key = f"spider_error/{failure.type.__name__}"
            stats.inc_value(key, 1)
            stats.set_value("last_error_message", str(failure.value))
            stats.set_value("last_error_url", getattr(response, "url", ""))
        except Exception:
            pass

    def spider_closed(self, spider, reason):
        stats = dict(spider.crawler.stats.get_stats() or {})

        # Add elapsed time if missing
        start_time = stats.get("start_time")
        finish_time = stats.get("finish_time")
        if start_time and finish_time and "elapsed_time_seconds" not in stats:
            try:
                if isinstance(start_time, datetime) and isinstance(
                    finish_time, datetime
                ):
                    stats["elapsed_time_seconds"] = (
                        finish_time - start_time
                    ).total_seconds()
            except Exception:
                pass

        # Merge spider custom metrics if available
        business_metrics = getattr(spider, "metrics", {}) or {}
        all_metrics: Dict[str, Any] = {**stats, **business_metrics}

        # Extra fields for embed
        extra_fields: List[Dict[str, Any]] = []

        # Example: if spider has course_stats attribute
        course_stats = getattr(spider, "course_stats", None)
        if isinstance(course_stats, dict):
            course_id_count = len(course_stats.get("course_ids", set()))
            course_name_count = len(course_stats.get("course_names", set()))
            extra_fields.append(
                {
                    "name": "Course Statistics",
                    "value": f"Course IDs: {course_id_count}\nCourse Names: {course_name_count}",
                    "inline": True,
                }
            )

        teacher_id_count = stats.get("teacher_count/ids", 0)
        teacher_name_count = stats.get("teacher_count/names", 0)

        if teacher_id_count or teacher_name_count:
            extra_fields.append(
                {
                    "name": "Teacher Statistics",
                    "value": f"Teacher IDs: {teacher_id_count}\nTeacher Names: {teacher_name_count}",
                    "inline": True,
                }
            )

        title = f"🕷️ Scrapy: {spider.name} finished ({reason})"
        description = f"Service: `{self.service_name}` • Spider: `{spider.name}` • Reason: `{reason}`"

        payload = _build_discord_payload(
            title=title,
            description=description,
            stats=all_metrics,
            mentions=self.mentions,
            extra_fields=extra_fields if extra_fields else None,
            color=0x2ECC71 if reason == "finished" else 0xE74C3C,
        )

        if not self.webhook_url:
            self.logger.warning("DISCORD_WEBHOOK_URL not set; skipping notification.")
            return

        def _post():
            return send_discord_webhook(self.webhook_url, payload)

        d = deferToThread(_post)

        def _ok(result: Dict[str, Any]):
            sc = result.get("status_code")
            if sc and 200 <= sc < 300:
                self.logger.info("Discord webhook sent (%s).", sc)
            else:
                self.logger.error(
                    "Discord webhook failed (%s): %s", sc, result.get("text")
                )

        def _err(f):
            self.logger.error("Discord webhook exception: %s", f.getErrorMessage())

        d.addCallback(_ok)
        d.addErrback(_err)
