# Session screen

The session screen is the shared live surface where participants see the current game session and record score adjustments. It is the production home of the room-screen prototype's variant A, per ADR-0004.

## Settled direction

- Mobile-first, minimal UI: white/gray surfaces, one blue accent, system fonts, flexbox only (no grid), Tailwind CSS utility classes.
- The current participant's score appears as the hero card, followed by the remaining participants in rank order.
- Preset actions are additive `+1`, `+5`, and `+10` adjustments. `Custom` replaces the current score with an explicit total. Both write the new absolute total via `POST /sessions/{id}/scores/{user_id}`.
- Scores are editable only in `live` and `timed_out` states. Participants edit their own scores; the host edits anyone's via the API.
- Host lifecycle controls (start, finalize, discard) are shown only to the host, as small buttons above the score card.
- Live/offline connection state is a small status pill in the header; SSE reconnects automatically and a toast reports interruption.
- The room code is displayed in the header so participants can share it.
- The session screen replaces the interactive prototype (`room-prototype.tsx` removed); in-memory fixtures and the variant switcher are gone.

## Review

Run the app in Docker and open `http://localhost:5173/home`:

1. Register, then log in.
2. Create a session for a game.
3. Start the session, tap `+1`/`+5`/`+10` or `Custom`, and watch the score update live.
4. Finalize the session and open the leaderboard to see the result.

## Follow-on API requirement

Preset buttons write absolute totals (the only write the API supports today). If simultaneous clients race, last write wins per metric. A future atomic increment endpoint (`POST /sessions/{id}/scores/{user_id}/adjust`) would remove the read-modify-write window.