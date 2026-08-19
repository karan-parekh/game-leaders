# PostgreSQL is the durable source of truth

Game Leaders uses PostgreSQL for users, sessions, participants, scores, and leaderboard inputs. The application keeps the first version operationally simple and leaves Redis for a later measured cache and multi-instance realtime phase.
