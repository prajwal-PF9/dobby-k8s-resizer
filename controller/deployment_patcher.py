def patch_deployment_requests(apps_v1, namespace: str, deployment_name: str, patches: list) -> None:
    """Patch only resources.requests on the named containers. Never touches limits."""
    body = {
        "spec": {
            "template": {
                "spec": {
                    "containers": patches
                }
            }
        }
    }
    apps_v1.patch_namespaced_deployment(deployment_name, namespace, body)
