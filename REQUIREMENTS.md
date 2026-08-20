# Board Game Leaderboard
This is a simple leaderboard for local board game groups to track their scores over time. (Scaling Reads and Real Time Updates)

## Functional Requirements
User should be able to
- register and logn with username and password (no email required)
- create a game session, discovered through its room code
    - Add a game to it
    - Update capacity if required
- view available sessions and their capacity
- join or leave a session
- update their/other's scores

## Non Functional Requirements
- The system should be more consistent than available
- Data should be durable for a long time and correct
- The UI should work on mobile first (Web interface to follow)
- If the system fails to update a score or join a session, it should notify the user with a toast notification
- The system needs to handle reads more than writes
- The system expects scores to be updated in real time


## Miscellaneous Features
- Create a leaderboard for each game, plus a global leaderboard across games
- Pull boardgame meta data from BGG API every 24 hours
- Allow users to leave review and feedback for the app

## Core Entities

## APIs

## High Level Design

## User Interface
