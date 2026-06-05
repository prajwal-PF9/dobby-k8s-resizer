from unittest.mock import MagicMock, patch
from controller.config import Config
from controller.scheduler import run_once
from controller.vpa_reader import WorkloadRec, ContainerRec


def _make_config(auto_apply=False, threshold=20.0):
    return Config(
        slack_bot_token="xoxb-test",
        slack_app_token="xapp-test",
        slack_signing_secret="secret",
        slack_channel="#k8s-resources",
        auto_apply_enabled=auto_apply,
        threshold_percent=threshold,
        schedule_interval_minutes=60,
        namespaces=["prajwal-hack"],
        node_instance_type="m5.xlarge",
    )


def _make_rec_above_threshold():
    # current=500m, rec=100m → 80% delta, above 20% threshold
    return WorkloadRec(
        namespace="prajwal-hack",
        deployment="over-app",
        containers=[
            ContainerRec(
                name="app",
                current_cpu_m=500.0,
                current_mem_bytes=1024 ** 3,
                rec_cpu_m=100.0,
                rec_mem_bytes=256 * 1024 ** 2,
            )
        ],
    )


def _make_rec_below_threshold():
    # current=500m, rec=450m → 10% delta, below 20% threshold
    return WorkloadRec(
        namespace="prajwal-hack",
        deployment="fine-app",
        containers=[
            ContainerRec(
                name="app",
                current_cpu_m=500.0,
                current_mem_bytes=1024 ** 3,
                rec_cpu_m=450.0,
                rec_mem_bytes=900 * 1024 ** 2,
            )
        ],
    )


@patch("controller.scheduler.list_recommendations")
@patch("controller.scheduler.post_message")
def test_run_once_posts_recommendation_when_auto_apply_off(mock_post, mock_list_recs):
    mock_list_recs.return_value = [_make_rec_above_threshold()]
    slack_client = MagicMock()
    custom_api = MagicMock()
    apps_v1 = MagicMock()

    run_once(_make_config(auto_apply=False), custom_api, apps_v1, slack_client)

    mock_post.assert_called_once()


@patch("controller.scheduler.list_recommendations")
@patch("controller.scheduler.patch_deployment_requests")
@patch("controller.scheduler.post_message")
def test_run_once_applies_when_auto_apply_on(mock_post, mock_patch, mock_list_recs):
    mock_list_recs.return_value = [_make_rec_above_threshold()]
    slack_client = MagicMock()
    custom_api = MagicMock()
    apps_v1 = MagicMock()

    run_once(_make_config(auto_apply=True), custom_api, apps_v1, slack_client)

    mock_patch.assert_called_once()
    mock_post.assert_called_once()


@patch("controller.scheduler.list_recommendations")
@patch("controller.scheduler.post_message")
def test_run_once_skips_below_threshold(mock_post, mock_list_recs):
    mock_list_recs.return_value = [_make_rec_below_threshold()]
    slack_client = MagicMock()
    custom_api = MagicMock()
    apps_v1 = MagicMock()

    run_once(_make_config(auto_apply=False, threshold=20.0), custom_api, apps_v1, slack_client)

    mock_post.assert_not_called()


@patch("controller.scheduler.list_recommendations")
@patch("controller.scheduler.post_message")
def test_run_once_skips_annotated_workloads(mock_post, mock_list_recs):
    rec = _make_rec_above_threshold()
    rec.skip = True
    mock_list_recs.return_value = [rec]
    slack_client = MagicMock()
    custom_api = MagicMock()
    apps_v1 = MagicMock()

    run_once(_make_config(auto_apply=False), custom_api, apps_v1, slack_client)

    mock_post.assert_not_called()


@patch("controller.scheduler.list_recommendations")
@patch("controller.scheduler.patch_deployment_requests")
@patch("controller.scheduler.post_message")
def test_run_once_posts_error_when_patch_fails(mock_post, mock_patch, mock_list_recs):
    mock_list_recs.return_value = [_make_rec_above_threshold()]
    mock_patch.side_effect = Exception("K8s API error")
    slack_client = MagicMock()
    custom_api = MagicMock()
    apps_v1 = MagicMock()

    run_once(_make_config(auto_apply=True), custom_api, apps_v1, slack_client)

    # Should post an error message, not crash
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    blocks = call_args[0][2]
    assert any("error" in str(b).lower() or "x" in str(b).lower() for b in blocks)
