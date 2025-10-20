# optimized_xtts.py
import asyncio
import numpy as np
import torch
from TTS.api import TTS


# === CONFIG ===
REFERENCE_WAV = "./recording_1760540826.wav"
LANGUAGE = "en"
DEVICE = "cuda"
USE_FP16 = False
SPEED = 1.2

# # Reduce sampling complexity for faster inference
# GENERATION_SETTINGS = {
#     "do_sample": True,         # ✅ Enable sampling
#     "top_k": 50,               # ✅ Limit to top 50 tokens
#     "top_p": 0.95,             # ✅ Nucleus sampling
#     "temperature": 1.0,        # ✅ Balanced creativity
#     "num_beams": 1,            # ✅ No beam search
#     "repetition_penalty": 1.0  # ✅ Avoid loops
# }
print("Loading XTTSv2...")
tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False)
tts.to(DEVICE)

xtts_model = tts.synthesizer

if USE_FP16:
    xtts_model.tts_model.gpt.half()
    print("✅ FP16 enabled for TTS v0.22")

# Warm-up
print("Warming up...")
with torch.amp.autocast('cuda', enabled=USE_FP16):
    _ = tts.tts(
        text="Ready.",
        speaker_wav=REFERENCE_WAV,
        language=LANGUAGE,
        speed=SPEED
    )
print("🔥 Ready!\n")


async def generate_audio_sync(text: str):
    loop = asyncio.get_event_loop()

    def _tts():
        with torch.amp.autocast('cuda', enabled=USE_FP16):
            return tts.tts(
                text=text,
                speaker_wav=REFERENCE_WAV,
                language=LANGUAGE,
                speed=SPEED
            )

    wav = await loop.run_in_executor(None, _tts)

    samples = np.array(wav).astype(np.float32)
    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples /= max_val

    class AudioChunk:
        def __init__(self, samples, sr):
            self.samples = samples
            self.sample_rate = sr

    return AudioChunk(samples, tts.synthesizer.output_sample_rate)


# # === Test ===
# if __name__ == "__main__":
#     async def test():
#         for txt in ["Hi!", "Hello.", "How can I help?"]:
#             start = asyncio.get_event_loop().time()
#             chunk = await generate_audio_sync(txt)
#             elapsed = asyncio.get_event_loop().time() - start
#             print(f"'{txt}' → {elapsed:.2f}s | {len(chunk.samples)} samples")

#     asyncio.run(test())

# === Test ===
if __name__ == "__main__":
    async def test():
        for txt in ["Hi!", "Hello.", "How can I help?", "Hello my name is rupak how can i help you today"]:
            start = asyncio.get_event_loop().time()
            chunk = await generate_audio_sync(txt)
            elapsed = asyncio.get_event_loop().time() - start
            print(f"'{txt}' → {elapsed:.2f}s | {len(chunk.samples)} samples")

    asyncio.run(test())