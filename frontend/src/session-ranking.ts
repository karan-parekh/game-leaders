export type RankedParticipant = {
  user_id: string;
  active: boolean;
  scores: Record<string, number>;
};

export function totalScore(participant: RankedParticipant) {
  return Object.values(participant.scores).reduce((sum, value) => sum + value, 0);
}

export function rankParticipants(participants: RankedParticipant[], direction: string) {
  const multiplier = direction === "low" ? 1 : -1;
  return participants
    .filter((participant) => participant.active)
    .sort((a, b) => multiplier * (totalScore(a) - totalScore(b)));
}

export function rankOf(participants: RankedParticipant[], direction: string, userId: string) {
  return rankParticipants([...participants], direction).findIndex((participant) => participant.user_id === userId) + 1;
}
