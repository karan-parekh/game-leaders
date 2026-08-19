# Game Leaders

The shared vocabulary for live board-game sessions, score entry, and community leaderboards.

## People and access

**User**:
A person with an immutable username and password who can participate in game sessions.
_Avoid_: Account, player (when referring to the person generally)

**Host**:
The user who creates a game session and controls its lifecycle and corrections.
_Avoid_: Owner, administrator

**Participant**:
A user recorded as a member of a game session.
_Avoid_: Attendee, player (when referring to membership rather than the person)

## Games and scoring

**Game definition**:
A curated board game with its default timeout, ranking direction, and default numeric scoring metrics.
_Avoid_: Game template, catalog item

**Metric**:
A named numeric field used to record part of a participant's score.
_Avoid_: Attribute, statistic

**Game session**:
One hosted play of a game definition, including its participants, current scores, and lifecycle state.
_Avoid_: Table, room (room is only the discovery surface for a session)

**Room code**:
The six-character code used to find a game session.
_Avoid_: Invite code, table ID

## Results

**Provisional result**:
The current score snapshot of a timed-out session that may still be replaced when the session resumes.
_Avoid_: Final score, draft result

**Finalized result**:
A host-approved game session result that permanently contributes to the leaderboard.
_Avoid_: Submitted result, completed score

**Leaderboard**:
A per-game ranking of users based on their best finalized result, with ties sharing rank.
_Avoid_: Ranking table, standings (when referring to the product concept)
