import json

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Task, UnsupportedOperationError
from a2a.utils import new_agent_text_message
from a2a.utils.errors import ServerError
from src.main import run_hedge_fund


class VanillaAgent:
    async def invoke(self, message: dict) -> str:
        result = run_hedge_fund(**message)
        return json.dumps(result)


class VanillaAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = VanillaAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        result = await self.agent.invoke(json.loads(context.get_user_input()))
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
