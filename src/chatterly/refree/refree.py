class Referee:
    async def analyze(self, agent_chunk, user_chunks):
        score = 0.7 if user_chunks else 0.0
        followup = "Can you elaborate?" if score < 0.5 else None
        return score, followup