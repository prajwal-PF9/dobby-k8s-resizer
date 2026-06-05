import time
import logging

from controller.vpa_reader import list_recommendations
from controller.cost_calculator import cpu_delta_percent, mem_delta_percent
from controller.deployment_patcher import patch_deployment_requests
from controller.slack_notifier import (
    build_recommendation_blocks,
    build_applied_blocks,
    build_error_blocks,
    post_message,
)

logger = logging.getLogger(__name__)


def _exceeds_threshold(rec, threshold_percent: float) -> bool:
    for c in rec.containers:
        if cpu_delta_percent(c.current_cpu_m, c.rec_cpu_m) > threshold_percent:
            return True
        if mem_delta_percent(c.current_mem_bytes, c.rec_mem_bytes) > threshold_percent:
            return True
    return False


def run_once(config, custom_api, apps_v1, slack_client) -> None:
    """Run one recommendation/apply cycle across all configured namespaces."""
    actionable = []

    for namespace in config.namespaces:
        try:
            recs = list_recommendations(custom_api, apps_v1, namespace)
        except Exception as e:
            logger.error("Failed to list recommendations for %s: %s", namespace, e)
            post_message(slack_client, config.slack_channel, build_error_blocks(str(e)))
            continue

        for rec in recs:
            if rec.skip:
                continue
            if _exceeds_threshold(rec, config.threshold_percent):
                actionable.append(rec)

    if not actionable:
        logger.info("No actionable recommendations this cycle.")
        return

    if config.auto_apply_enabled:
        applied = []
        for rec in actionable:
            patches = [
                {
                    "name": c.name,
                    "resources": {
                        "requests": {
                            "cpu": f"{int(c.rec_cpu_m)}m",
                            "memory": f"{c.rec_mem_bytes // (1024 ** 2)}Mi",
                        }
                    },
                }
                for c in rec.containers
            ]
            try:
                patch_deployment_requests(apps_v1, rec.namespace, rec.deployment, patches)
                for c in rec.containers:
                    applied.append({
                        "namespace": rec.namespace,
                        "deployment": rec.deployment,
                        "container": c.name,
                        "cpu": f"{int(c.rec_cpu_m)}m",
                        "memory": f"{c.rec_mem_bytes // (1024 ** 2)}Mi",
                    })
            except Exception as e:
                logger.error("Failed to patch %s/%s: %s", rec.namespace, rec.deployment, e)
                post_message(
                    slack_client,
                    config.slack_channel,
                    build_error_blocks(f"Failed to patch {rec.namespace}/{rec.deployment}: {e}"),
                )

        if applied:
            post_message(slack_client, config.slack_channel, build_applied_blocks(applied))
    else:
        post_message(
            slack_client,
            config.slack_channel,
            build_recommendation_blocks(actionable, config.node_instance_type),
        )


def run_scheduler(config, custom_api, apps_v1, slack_client) -> None:
    """Infinite loop: run_once every N minutes."""
    logger.info(
        "Scheduler started. Interval: %d min, namespaces: %s",
        config.schedule_interval_minutes,
        config.namespaces,
    )
    while True:
        try:
            run_once(config, custom_api, apps_v1, slack_client)
        except Exception as e:
            logger.error("Unhandled scheduler error: %s", e)
            try:
                post_message(slack_client, config.slack_channel, build_error_blocks(str(e)))
            except Exception:
                pass
        time.sleep(config.schedule_interval_minutes * 60)
