from unittest.mock import MagicMock
from controller.slack_notifier import build_recommendation_blocks, build_applied_blocks, build_error_blocks, post_message
from controller.vpa_reader import WorkloadRec, ContainerRec


def _make_rec(ns, dep, cur_cpu_m, rec_cpu_m, cur_mem_bytes, rec_mem_bytes):
    return WorkloadRec(
        namespace=ns,
        deployment=dep,
        containers=[
            ContainerRec(
                name="app",
                current_cpu_m=cur_cpu_m,
                current_mem_bytes=cur_mem_bytes,
                rec_cpu_m=rec_cpu_m,
                rec_mem_bytes=rec_mem_bytes,
            )
        ],
    )


def test_build_recommendation_blocks_contains_deployment_name():
    rec = _make_rec("prajwal-hack", "my-app", 500.0, 100.0, 1024**3, 256*1024**2)
    blocks = build_recommendation_blocks([rec], "m5.xlarge")
    text = str(blocks)
    assert "my-app" in text
    assert "prajwal-hack" in text


def test_build_recommendation_blocks_shows_cost():
    rec = _make_rec("prajwal-hack", "my-app", 500.0, 100.0, 1024**3, 256*1024**2)
    blocks = build_recommendation_blocks([rec], "m5.xlarge")
    text = str(blocks)
    assert "$" in text


def test_build_recommendation_blocks_is_list():
    rec = _make_rec("prajwal-hack", "my-app", 500.0, 100.0, 1024**3, 256*1024**2)
    blocks = build_recommendation_blocks([rec], "m5.xlarge")
    assert isinstance(blocks, list)
    assert len(blocks) > 0


def test_build_applied_blocks_contains_deployment():
    applied = [{"namespace": "prajwal-hack", "deployment": "my-app",
                "container": "app", "cpu": "100m", "memory": "256Mi"}]
    blocks = build_applied_blocks(applied)
    text = str(blocks)
    assert "my-app" in text
    assert "100m" in text


def test_build_error_blocks_contains_message():
    blocks = build_error_blocks("something went wrong")
    text = str(blocks)
    assert "something went wrong" in text


def test_post_message_calls_slack_client():
    client = MagicMock()
    post_message(client, "#k8s-resources", [{"type": "section", "text": {"type": "mrkdwn", "text": "hello"}}])
    client.chat_postMessage.assert_called_once()
    call_kwargs = client.chat_postMessage.call_args[1]
    assert call_kwargs["channel"] == "#k8s-resources"
