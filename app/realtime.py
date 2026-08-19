import asyncio
from collections import defaultdict


class SessionHub:
    def __init__(self) -> None:
        self._listeners: dict[str, set[asyncio.Queue[dict]]] = defaultdict(set)

    def subscribe(self, session_id: str) -> asyncio.Queue[dict]:
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=10)
        self._listeners[session_id].add(queue)
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue[dict]) -> None:
        self._listeners[session_id].discard(queue)

    async def publish(self, session_id: str, snapshot: dict) -> None:
        for queue in tuple(self._listeners[session_id]):
            if queue.full():
                queue.get_nowait()
            await queue.put(snapshot)


hub = SessionHub()
