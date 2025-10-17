
import numpy as np 
import sounddevice as sd
import asyncio

import time
import functools
import asyncio 
import logging 


# # Load XTTSv2 once (outside the function for performance)
# Allowlist XTTSv2 config classes
from TTS.api import TTS

from logger import setup_daily_logger

class LogExecutionTime:
    def __init__(self, label=None):
        self.logger = setup_daily_logger()
        self.label = label or "Execution"

    def __call__(self, func):
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                self.logger.info(f"⏱️ {self.label} took {elapsed:.2f} seconds.")
                return result
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                self.logger.info(f"⏱️ {self.label} took {elapsed:.2f} seconds.")
                return result
        return wrapper


class AudioChunk:
    def __init__(self, data, frame_rate):
        self.data = data
        self.frame_rate = frame_rate
        self.timestamp = asyncio.get_event_loop().time()

@LogExecutionTime(label="Load Model")
async def load_model():
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
    return tts 

@LogExecutionTime(label="Generate Audio Chunks")
async def generate_audio_sync(tts, text):
    wav = tts.tts(text,
                  speaker_wav="./recording_1760540826.wav",
                  language="en")  # Returns NumPy array of PCM samples
    samples = np.array(wav).astype("float32")  # Convert list to NumPy array and cast to float32
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples /= max_val
    return AudioChunk(samples, tts.synthesizer.output_sample_rate)

@LogExecutionTime(label="Playing audio")
async def play(chunk):
    print("🔊 Playing agent audio...")
    sd.play(chunk.data, chunk.frame_rate)
    await asyncio.sleep(len(chunk.data) / chunk.frame_rate)  # Wait for playback to finish
    sd.stop()

@LogExecutionTime(label="Playing audio")
async def agent_speaking_with_output_stream(chunk):
    print("🔊 Playing agent audio...")

    audio = chunk.data.astype(np.float32)
    samplerate = chunk.frame_rate

    def callback(outdata, frames, time, status):
        if status:
           logger.warning(f"Playback status: {status}")
        chunk = audio[callback.pos:callback.pos + frames]
        if len(chunk) < frames:
            outdata[:len(chunk)] = chunk.reshape(-1, 1)
            outdata[len(chunk):] = 0
            raise sd.CallbackStop()
        else:
            outdata[:] = chunk.reshape(-1, 1)
        callback.pos += frames

    callback.pos = 0

    with sd.OutputStream(samplerate=samplerate, channels=1, dtype='float32', callback=callback):
        duration = len(audio) / samplerate
        await asyncio.sleep(duration)

    logger.info("✅ Agent finished speaking, asking vad thread to proceed")



logger = setup_daily_logger()

async def run():
    logger.info("Starting session...")
    text = "Hello how are you doing today"
    tts = await load_model()
    chunk = await generate_audio_sync(tts, text)
    await agent_speaking_with_output_stream(chunk)

def run_session_in_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run())
    loop.close()

import threading 
def run_main():
    session_thread = threading.Thread(target=run_session_in_thread)
    session_thread.start()
    try:
        while session_thread.is_alive():
            session_thread.join(timeout=1)
    except KeyboardInterrupt:
        print("\n[Main] Ctrl+C received. Shutting down...")
    finally:
        print("[Main] SessionManager thread exited.")

if __name__ == "__main__":
    run_main()
    
