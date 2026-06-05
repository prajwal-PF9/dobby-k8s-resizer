from unittest.mock import MagicMock
from controller.deployment_patcher import patch_deployment_requests


def test_patch_deployment_requests_calls_k8s_api():
    apps_v1 = MagicMock()

    patch_deployment_requests(
        apps_v1=apps_v1,
        namespace="prajwal-hack",
        deployment_name="my-app",
        patches=[{"name": "app", "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}}}],
    )

    apps_v1.patch_namespaced_deployment.assert_called_once_with(
        "my-app",
        "prajwal-hack",
        {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {"name": "app", "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}}}
                        ]
                    }
                }
            }
        },
    )


def test_patch_deployment_requests_multiple_containers():
    apps_v1 = MagicMock()

    patches = [
        {"name": "app", "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}}},
        {"name": "sidecar", "resources": {"requests": {"cpu": "50m", "memory": "64Mi"}}},
    ]
    patch_deployment_requests(apps_v1, "prajwal-hack", "my-app", patches)

    body = apps_v1.patch_namespaced_deployment.call_args[0][2]
    containers = body["spec"]["template"]["spec"]["containers"]
    assert len(containers) == 2
    assert containers[0]["name"] == "app"
    assert containers[0]["resources"]["requests"]["cpu"] == "100m"
    assert containers[0]["resources"]["requests"]["memory"] == "256Mi"
    assert containers[1]["name"] == "sidecar"
    assert containers[1]["resources"]["requests"]["cpu"] == "50m"
    assert containers[1]["resources"]["requests"]["memory"] == "64Mi"


def test_patch_does_not_include_limits():
    apps_v1 = MagicMock()

    patch_deployment_requests(
        apps_v1=apps_v1,
        namespace="prajwal-hack",
        deployment_name="my-app",
        patches=[{"name": "app", "resources": {"requests": {"cpu": "100m", "memory": "256Mi"}}}],
    )

    body = apps_v1.patch_namespaced_deployment.call_args[0][2]
    container = body["spec"]["template"]["spec"]["containers"][0]
    assert "limits" not in container.get("resources", {})
