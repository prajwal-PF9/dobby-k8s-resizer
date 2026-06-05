from unittest.mock import MagicMock
from controller.vpa_reader import list_recommendations, WorkloadRec, ContainerRec


def _make_vpa(name, namespace, container_recs, annotations=None):
    return {
        "metadata": {
            "name": name,
            "namespace": namespace,
            "annotations": annotations or {},
        },
        "spec": {"targetRef": {"kind": "Deployment", "name": name}},
        "status": {
            "recommendation": {
                "containerRecommendations": container_recs
            }
        },
    }


def _make_deployment(container_name, cpu_req, mem_req):
    container = MagicMock()
    container.name = container_name
    container.resources.requests = {"cpu": cpu_req, "memory": mem_req}
    deployment = MagicMock()
    deployment.spec.template.spec.containers = [container]
    return deployment


def test_list_recommendations_returns_workload_recs():
    custom_api = MagicMock()
    apps_v1 = MagicMock()

    vpa_item = _make_vpa(
        "my-app", "prajwal-hack",
        [{"containerName": "app", "target": {"cpu": "100m", "memory": "256Mi"}}],
    )
    custom_api.list_namespaced_custom_object.return_value = {"items": [vpa_item]}
    apps_v1.read_namespaced_deployment.return_value = _make_deployment("app", "500m", "1Gi")

    recs = list_recommendations(custom_api, apps_v1, "prajwal-hack")

    assert len(recs) == 1
    assert recs[0].deployment == "my-app"
    assert recs[0].namespace == "prajwal-hack"
    assert len(recs[0].containers) == 1
    assert recs[0].containers[0].name == "app"
    assert recs[0].containers[0].current_cpu_m == 500.0
    assert recs[0].containers[0].rec_cpu_m == 100.0


def test_list_recommendations_skip_annotation():
    custom_api = MagicMock()
    apps_v1 = MagicMock()

    vpa_item = _make_vpa(
        "skip-app", "prajwal-hack",
        [{"containerName": "app", "target": {"cpu": "100m", "memory": "256Mi"}}],
        annotations={"hack-resizer/skip": "true"},
    )
    custom_api.list_namespaced_custom_object.return_value = {"items": [vpa_item]}
    apps_v1.read_namespaced_deployment.return_value = _make_deployment("app", "500m", "1Gi")

    recs = list_recommendations(custom_api, apps_v1, "prajwal-hack")

    assert len(recs) == 1
    assert recs[0].skip is True


def test_list_recommendations_no_status():
    custom_api = MagicMock()
    apps_v1 = MagicMock()

    vpa_item = {
        "metadata": {"name": "no-status-app", "namespace": "prajwal-hack", "annotations": {}},
        "spec": {"targetRef": {"kind": "Deployment", "name": "no-status-app"}},
        "status": {},
    }
    custom_api.list_namespaced_custom_object.return_value = {"items": [vpa_item]}

    recs = list_recommendations(custom_api, apps_v1, "prajwal-hack")

    assert recs == []


def test_list_recommendations_deployment_not_found_skipped():
    custom_api = MagicMock()
    apps_v1 = MagicMock()

    vpa_item = _make_vpa(
        "missing-app", "prajwal-hack",
        [{"containerName": "app", "target": {"cpu": "100m", "memory": "256Mi"}}],
    )
    custom_api.list_namespaced_custom_object.return_value = {"items": [vpa_item]}
    apps_v1.read_namespaced_deployment.side_effect = Exception("Not found")

    recs = list_recommendations(custom_api, apps_v1, "prajwal-hack")

    assert recs == []
