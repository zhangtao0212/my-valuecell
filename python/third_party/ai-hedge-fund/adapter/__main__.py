import json
import logging
import sys
from pathlib import Path

import click
import httpx
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import (
    BasePushNotificationSender,
    InMemoryPushNotificationConfigStore,
    InMemoryTaskStore,
)
from a2a.types import AgentCard
from adapter.agent_executor import VanillaAgentExecutor

logger = logging.getLogger(__name__)


@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10001)
@click.option('--agent-card', 'agent_card_file')
def main(host, port, agent_card_file):
    """Starts an Agent server."""
    try:
        if not agent_card_file:
            raise ValueError('Agent card is required')
        with Path.open(agent_card_file) as file:
            data = json.load(file)
        agent_card = AgentCard(**data)

        client = httpx.AsyncClient()
        push_notification_config_store = InMemoryPushNotificationConfigStore()
        push_notification_sender = BasePushNotificationSender(
            client, config_store=push_notification_config_store
        )

        request_handler = DefaultRequestHandler(
            agent_executor=VanillaAgentExecutor(),
            task_store=InMemoryTaskStore(),
            push_config_store=push_notification_config_store,
            push_sender=push_notification_sender,
        )

        server = A2AStarletteApplication(
            agent_card=agent_card, http_handler=request_handler
        )

        logger.info(f'Starting server on {host}:{port}')

        uvicorn.run(server.build(), host=host, port=port)
    except FileNotFoundError:
        logger.error(f"Error: File '{agent_card_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Error: File '{agent_card_file}' contains invalid JSON.")
        sys.exit(1)
    except Exception as e:
        logger.error(f'An error occurred during server startup: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
