# SSE broadcasts full committed snapshots

The session SSE stream broadcasts the complete committed session snapshot after each accepted score or lifecycle mutation. This makes reconnect and client recovery straightforward, while the initial single-process hub can later be replaced by Redis pub/sub without changing the client contract.
