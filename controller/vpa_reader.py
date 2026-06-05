from dataclasses import dataclass, field
from controller.cost_calculator import parse_cpu_to_millicores, parse_memory_to_bytes


@dataclass
class ContainerRec:
    name: str
    current_cpu_m: float
    current_mem_bytes: int
    rec_cpu_m: float
    rec_mem_bytes: int


@dataclass
class WorkloadRec:
    namespace: str
    deployment: str
    containers: list = field(default_factory=list)
    skip: bool = False


def list_recommendations(custom_api, apps_v1, namespace: str) -> list:
    """List all VPA recommendations for Deployments in the given namespace."""
    response = custom_api.list_namespaced_custom_object(
        group="autoscaling.k8s.io",
        version="v1",
        namespace=namespace,
        plural="verticalpodautoscalers",
    )

    results = []
    for item in response.get("items", []):
        meta = item.get("metadata", {})
        annotations = meta.get("annotations") or {}
        skip = annotations.get("hack-resizer/skip", "false").lower() == "true"

        # Goldilocks names VPAs as "goldilocks-<deployment>" — use targetRef for the real name
        deployment_name = item.get("spec", {}).get("targetRef", {}).get("name", "")
        if not deployment_name:
            continue

        status = item.get("status", {})
        recommendation = status.get("recommendation", {})
        container_recs = recommendation.get("containerRecommendations", [])
        if not container_recs:
            continue

        try:
            deployment = apps_v1.read_namespaced_deployment(deployment_name, namespace)
        except Exception:
            continue

        current_requests = {}
        for c in deployment.spec.template.spec.containers:
            reqs = c.resources.requests or {}
            current_requests[c.name] = {
                "cpu": reqs.get("cpu", "0m"),
                "memory": reqs.get("memory", "0Mi"),
            }

        containers = []
        for crec in container_recs:
            cname = crec["containerName"]
            target = crec.get("target", {})
            cur = current_requests.get(cname, {"cpu": "0m", "memory": "0Mi"})
            containers.append(
                ContainerRec(
                    name=cname,
                    current_cpu_m=parse_cpu_to_millicores(cur["cpu"]),
                    current_mem_bytes=parse_memory_to_bytes(cur["memory"]),
                    rec_cpu_m=parse_cpu_to_millicores(target.get("cpu", "0m")),
                    rec_mem_bytes=parse_memory_to_bytes(target.get("memory", "0Mi")),
                )
            )

        results.append(
            WorkloadRec(namespace=namespace, deployment=deployment_name, containers=containers, skip=skip)
        )

    return results
