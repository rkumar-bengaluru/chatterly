class Referee:

    async def analyze(self, agent, user):
        score = 0.7 if user else 0.0
        followup = "can you elaborate" if score < 0.5 else None 
        return score, followup