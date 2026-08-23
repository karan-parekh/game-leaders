# Board Game Leaderboard
This is a simple leaderboard for local board game groups to track their scores over time. (Scaling Reads and Real Time Updates)

## Functional Requirements
User should be able to
- register and logn with username and password (no email required)
- create a table (room)
    - add a game to it
    - update capacity if required
    - invite users via username
    - create a shareable link
- view available tables and it's capacity
- join or leave a table
- update their/other's scores

## Non Functional Requirements
- The system should be more consistent than available
- Data should be durable for a long time and correct
- The UI should work on mobile first (Web interface to follow)
- If the system fails to update a score or join a table, it should notify the user with a toast notification
- The system needs to handle reads more than writes
- The system expects scores to be updated in real time

## Miscellaneous Features
- Create a default leaderboard for each table with the default metrics of points 
- Pull boardgame meta data from BGG API every 24 hours
- Allow users to leave review and feedback for the app

## Core Entities
- User
- Game
- Table
- Score  // Keeps track of points scored by the user per game per table

## APIs
**Authentication**

Register user
```
POST /auth/register -> redirect to login
    body {
        username: string,
        password: string
    }
```
Login user
```    
POST /auth/login -> auth token
    body {
        username: string,
        password: string
    }
```
**Games**
```
GET /games -> Game[]
```
**Tables**
```
POST /tables -> redirect to table view
    body {
        name: string,
        game: {game_id},
    }
```
```
POST /tables/{table_id}/invite -> 200 OK
    body {
        users: List[{user_id}]
    }
```
```
PATCH /tables/{table_id}/join -> 200 OK
    body {
        user: {user_id}
    }
```
```
PATCH /tables/{table_id}/leave -> 200 OK
    body {
        user: {user_id}
    }
```
```
GET /tables -> Table[]
```
**Scores**
```
POST 
```
```
PATCH
```
```
GET
```
## High Level Design


## User Interface
