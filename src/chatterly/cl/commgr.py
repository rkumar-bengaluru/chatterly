import asyncio
from chatterly.cl.comloop import CommunicationLoop
from faster_whisper import WhisperModel

class CommunicationLoopMgr:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def init(self):
        self.whisper_model = await asyncio.to_thread(
            WhisperModel, "small.en", compute_type="auto"
        )

    async def add_new_loop(self, agent_chunk):
        await self.init()
        loop = CommunicationLoop(self.whisper_model,agent_chunk)
        await self.queue.put(loop)

    async def requeue(self, loop):
        await self.queue.put(loop)

    async def process(self):
        while not self.queue.empty():
            loop = await self.queue.get()
            await loop.run()