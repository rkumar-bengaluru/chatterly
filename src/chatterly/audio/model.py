from faster_whisper import WhisperModel
from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
from chatterly.utils.logger import setup_daily_logger

import asyncio 
import numpy as np

class AudioModel:

    def __init__(self,audio_model):
        # self.whisper_model = WhisperModel("small.en", device="cpu", compute_type="int8")
        
        self.audio_model = audio_model
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)
        self.logger.info("whisper model loaded...")

    async def transcribe_frames(self, buffer):
        try:
            segments_gen = await asyncio.to_thread(
                self.audio_model.transcribe,
                buffer.astype(np.float32) / 32768.0,
                language="en",
                beam_size=1,
                word_timestamps=False,
                task="transcribe"
            )
            print(segments_gen)

           
            transcription = "".join(segment.text for segment in segments_gen).strip()
            return transcription
        except Exception as e:
            self.logger.error(f"Transcription failed: {str(e)}")
            raise Exception(f"Transcription failed: {str(e)}")