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


class LeaderboardHub:
    def __init__(self) -> None:
        self._listeners: dict[str, set[asyncio.Queue[list[dict]]]] = defaultdict(set)

    def subscribe(self, game_id: str) -> asyncio.Queue[list[dict]]:
        queue: asyncio.Queue[list[dict]] = asyncio.Queue(maxsize=5)
        self._listeners[game_id].add(queue)
        return queue

    def unsubscribe(self, game_id: str, queue: asyncio.Queue[list[dict]]) -> None:
        self._listeners[game_id].discard(queue)

    async def publish(self, game_id: str, rows: list[dict]) -> None:
        for queue in tuple(self._listeners[game_id]):
            if queue.full():
                queue.get_nowait()
            await queue.put(rows)


hub = SessionHub()
leaderboard_hub = LeaderboardHub()
