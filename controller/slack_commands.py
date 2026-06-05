import logging
from slack_bolt import App
from controller.scheduler import _exceeds_threshold
from controller.vpa_reader import list_recommendations
from controller.deployment_patcher import patch_deployment_requests
from controller.slack_notifier import (
    build_recommendation_blocks,
    build_applied_blocks,
    build_error_blocks,
    post_message,
)

logger = logging.getLogger(__name__)


def create_slack_app(config, custom_api, apps_v1) -> App:
    app = App(token=config.slack_bot_token, signing_secret=config.slack_signing_secret)

    @app.command("/resize")
    def handle_resize(ack, body, client):
        ack(":hourglass: Processing...")
        text = (body.get("text") or "").strip().lower()

        if text == "recommend":
            _cmd_recommend(config, custom_api, apps_v1, client)
        elif text == "apply":
            _cmd_apply(config, custom_api, apps_v1, client)
        elif text == "status":
            _cmd_status(config, custom_api, apps_v1, client)
        elif text in ("autoapply on", "autoapply off"):
            _cmd_autoapply(config, client, enabled=(text == "autoapply on"))
        else:
            client.chat_postMessage(
                channel=config.slack_channel,
                text=(
                    "Unknown subcommand. Usage:\n"
                    "`/resize recommend` — show recommendations\n"
                    "`/resize apply` — apply all recommendations now\n"
                    "`/resize status` — show current vs recommended\n"
                    "`/resize autoapply on|off` — toggle auto-apply"
                ),
            )

    return app


def _cmd_recommend(config, custom_api, apps_v1, client):
    actionable = []
    for namespace in config.namespaces:
        recs = list_recommendations(custom_api, apps_v1, namespace)
        for rec in recs:
            if not rec.skip and _exceeds_threshold(rec, config.threshold_percent):
                actionable.append(rec)

    if not actionable:
        client.chat_postMessage(
            channel=config.slack_channel,
            text=":white_check_mark: All workloads are within the threshold. No recommendations.",
        )
        return

    post_message(client, config.slack_channel,
                 build_recommendation_blocks(actionable, config.node_instance_type))


def _cmd_apply(config, custom_api, apps_v1, client):
    applied = []
    for namespace in config.namespaces:
        recs = list_recommendations(custom_api, apps_v1, namespace)
        for rec in recs:
            if rec.skip or not _exceeds_threshold(rec, config.threshold_percent):
                continue
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
                post_message(client, config.slack_channel,
                             build_error_blocks(f"Failed to patch {rec.deployment}: {e}"))

    if applied:
        post_message(client, config.slack_channel, build_applied_blocks(applied))
    else:
        client.chat_postMessage(
            channel=config.slack_channel,
            text=":white_check_mark: Nothing to apply — all workloads within threshold.",
        )


def _cmd_status(config, custom_api, apps_v1, client):
    lines = ["*Current vs Recommended Resource Requests*\n"]
    for namespace in config.namespaces:
        lines.append(f"*Namespace: `{namespace}`*")
        recs = list_recommendations(custom_api, apps_v1, namespace)
        if not recs:
            lines.append("  No VPA data yet.")
            continue
        for rec in recs:
            for c in rec.containers:
                cur_cpu = f"{int(c.current_cpu_m)}m"
                rec_cpu = f"{int(c.rec_cpu_m)}m"
                cur_mem = f"{c.current_mem_bytes // (1024**2)}Mi"
                rec_mem = f"{c.rec_mem_bytes // (1024**2)}Mi"
                lines.append(
                    f"  `{rec.deployment}/{c.name}`: "
                    f"CPU {cur_cpu}→{rec_cpu}  Mem {cur_mem}→{rec_mem}"
                )

    client.chat_postMessage(channel=config.slack_channel, text="\n".join(lines))


def _cmd_autoapply(config, client, enabled: bool):
    config.auto_apply_enabled = enabled
    state = "ON :rocket:" if enabled else "OFF :pause_button:"
    client.chat_postMessage(
        channel=config.slack_channel,
        text=f":gear: Auto-apply is now *{state}*",
    )
