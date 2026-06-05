import os
from dataclasses import dataclass


@dataclass
class Config:
    slack_bot_token: str
    slack_app_token: str
    slack_signing_secret: str
    slack_channel: str
    auto_apply_enabled: bool
    threshold_percent: float
    schedule_interval_minutes: int
    namespaces: list
    node_instance_type: str


def load_config() -> Config:
    return Config(
        slack_bot_token=os.environ["SLACK_BOT_TOKEN"],
        slack_app_token=os.environ["SLACK_APP_TOKEN"],
        slack_signing_secret=os.environ["SLACK_SIGNING_SECRET"],
        slack_channel=os.environ.get("SLACK_CHANNEL", "#k8s-resources"),
        auto_apply_enabled=os.environ.get("AUTO_APPLY_ENABLED", "false").lower() == "true",
        threshold_percent=float(os.environ.get("THRESHOLD_PERCENT", "20")),
        schedule_interval_minutes=int(os.environ.get("SCHEDULE_INTERVAL_MINUTES", "60")),
        namespaces=os.environ.get(
            "NAMESPACES", "prajwal-hack,prajwal-hack-region-1"
        ).split(","),
        node_instance_type=os.environ.get("NODE_INSTANCE_TYPE", "m5.xlarge"),
    )


def get_k8s_clients():
    """Returns (custom_objects_api, apps_v1_api, core_v1_api). Loads in-cluster config if available."""
    from kubernetes import client, config as k8s_config

    try:
        k8s_config.load_incluster_config()
    except k8s_config.ConfigException:
        k8s_config.load_kube_config()

    return (
        client.CustomObjectsApi(),
        client.AppsV1Api(),
        client.CoreV1Api(),
    )
