import asyncio

class AudioChunk:
    def __init__(self, data, frame_rate):
        self.data = data
        self.frame_rate = frame_rate
        self.timestamp = asyncio.get_event_loop().time()