import logging
import threading

from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk import WebClient

from controller.config import load_config, get_k8s_clients
from controller.scheduler import run_scheduler
from controller.slack_commands import create_slack_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    config = load_config()
    custom_api, apps_v1, _ = get_k8s_clients()
    slack_client = WebClient(token=config.slack_bot_token)

    logger.info("Starting scheduler thread...")
    scheduler_thread = threading.Thread(
        target=run_scheduler,
        args=(config, custom_api, apps_v1, slack_client),
        daemon=True,
        name="scheduler",
    )
    scheduler_thread.start()

    logger.info("Starting Slack socket mode listener...")
    app = create_slack_app(config, custom_api, apps_v1)
    handler = SocketModeHandler(app, config.slack_app_token)
    handler.start()


if __name__ == "__main__":
    main()
