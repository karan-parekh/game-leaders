import json
import subprocess
import unittest
from pathlib import Path


FRONTEND = Path(__file__).parents[1] / "frontend"


class SessionRankingTests(unittest.TestCase):
    def test_low_direction_puts_lower_total_first_and_ranks_it_first(self):
        result = subprocess.run(
            [
                "node",
                "--experimental-strip-types",
                "-e",
                "import { rankOf, rankParticipants } from './src/session-ranking.ts'; const participants = [{ user_id: 'high', active: true, scores: { points: 20 } }, { user_id: 'low', active: true, scores: { points: 10 } }]; console.log(JSON.stringify({ order: rankParticipants(participants, 'low').map((p) => p.user_id), rank: rankOf(participants, 'low', 'low') }));",
            ],
            cwd=FRONTEND,
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(json.loads(result.stdout), {"order": ["low", "high"], "rank": 1})
