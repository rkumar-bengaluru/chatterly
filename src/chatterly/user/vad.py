import webrtcvad
import sounddevice as sd
import numpy as np
import asyncio
import time
import os
import io
import wave
from faster_whisper import WhisperModel
import aiofiles
import queue

from chatterly.utils.constants import LOGGER_NAME, LOGGER_DIR
from chatterly.utils.logger import setup_daily_logger

class BufferedVADCapture:
    def __init__(self,vad_queue=None,cl_queue=None, sample_rate=16000, frame_ms=30, pause_ms=1000, vad_mode=2, channels=1, speech_hold_ms=600, short_silence_min_ms=150, short_silence_max_ms=300, callback=None):
        self.logger = setup_daily_logger(name=LOGGER_NAME, log_dir=LOGGER_DIR)
        if sample_rate not in [8000, 16000, 32000, 48000]:
            raise ValueError("Sample rate must be 8000, 16000, 32000, or 48000.")
        if frame_ms <= 0:
            raise ValueError("Frame duration must be positive.")
        if pause_ms < 0:
            raise ValueError("Pause duration cannot be negative.")
        
        self.VAD_LOG_FILE = "vad_log.txt"
        self.ERROR_LOG_FILE = "error_log.txt"
        
        # Audio configuration
        self.SAMPLE_RATE = sample_rate
        self.FRAME_DURATION = frame_ms / 1000  # Convert ms to seconds
        self.BLOCKSIZE = int(self.SAMPLE_RATE * self.FRAME_DURATION)
        self.SILENCE_FRAMES = pause_ms // frame_ms
        self.SPEECH_HOLD_FRAMES = speech_hold_ms // frame_ms
        self.SHORT_SILENCE_MIN = short_silence_min_ms // frame_ms
        self.SHORT_SILENCE_MAX = short_silence_max_ms // frame_ms
        self.VAD_MODE = vad_mode
        self.CHANNEL = channels
        
        self.audio_buffer = []
        self.pcm_buffer = []
        self.segment_counter = 0
        self.silence_counter = 0
        self.speech_hold_counter = 0
        self.is_speaking = False
        self.buffer_changed = False
        self.short_silence_transcribed = False
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(self.VAD_MODE)
        self.callback = callback if callback else self.self_callback
        self.log_queue = queue.Queue()  # Thread-safe queue for logging
        self.max_duration_s=30
        self.max_frames = int((self.max_duration_s * 1000) // frame_ms)
        self.frame_ms=30
        self.max_duration = self.max_frames * (self.frame_ms / 1000)
        self.vad_queue = vad_queue
        self.cl_queue = cl_queue
        
        # Initialize faster-whisper model
        try:
            self.whisper_model = WhisperModel("small.en", compute_type="auto")
            self.logger.info("whisper_model_loaded")
        except Exception as e:
            raise RuntimeError(f"Failed to load faster-whisper model: {e}")

    def self_callback(self, msg):
        self.logger.info(msg)

    def audio_callback(self, indata, frames, time_info, status):
        """Synchronous callback for processing audio frames."""
        start_time = time.time()
        
        if status:
            self.log_queue.put(("error", f"Error: {status} at time {time_info['current_time']}"))
            return
        
        # Store audio frame
        self.audio_buffer.append(indata.copy())
        pcm = (indata[:, 0] * 32768).clip(-32768, 32767).astype(np.int16).tobytes()
        self.pcm_buffer.append(pcm)
        self.buffer_changed = True
        
        # Perform VAD
        try:
            is_speech = self.vad.is_speech(pcm, sample_rate=self.SAMPLE_RATE)
            self.log_queue.put(("vad", f"Frame {len(self.audio_buffer)}: {'Speech' if is_speech else 'Silence'}"))
        except Exception as e:
            self.log_queue.put(("error", f"VAD error: {e}"))
            is_speech = False
        
        # Update state
        if not is_speech:
            self.silence_counter += 1
            self.speech_hold_counter = 0
        else:
            self.speech_hold_counter += 1
            if not self.is_speaking and self.speech_hold_counter >= self.SPEECH_HOLD_FRAMES:
                self.is_speaking = True
                self.silence_counter = 0
                self.short_silence_transcribed = False
                self.logger.info("speech_detected")
            elif self.is_speaking:
                self.silence_counter = 0
                self.short_silence_transcribed = False
        
        # Log callback duration if too long
        duration = (time.time() - start_time) * 1000
        if duration > self.FRAME_DURATION * 1000:
            self.log_queue.put(("error", f"Callback took {duration:.2f} ms, exceeds frame duration {self.FRAME_DURATION * 1000:.2f} ms"))

    async def process_log_queue(self):
        """Process log messages from the queue asynchronously."""
        while True:
            try:
                log_type, message = self.log_queue.get_nowait()
                async with aiofiles.open(
                    self.VAD_LOG_FILE if log_type == "vad" else self.ERROR_LOG_FILE,
                    mode='a'
                ) as f:
                    await f.write(f"{message}\n")
                if log_type == "error":
                    self.callback(message)
            except queue.Empty:
                break
            except Exception as e:
                self.callback(f"Log processing error: {e}")


    async def clear_log_files(self):
        """Asynchronously clear log files."""
        for log_file in [self.VAD_LOG_FILE, self.ERROR_LOG_FILE]:
            if await asyncio.to_thread(os.path.exists, log_file):
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, os.remove, log_file)

                self.callback(f"cleared_log_file: {log_file}")

    async def transcribe(self, audio_buffer):
        """
        Transcribe the captured audio buffer using faster-whisper.
        Returns the transcribed text or None if transcription fails.
        """
        if not audio_buffer:
            self.callback("empty_audio_buffer")
            return None

        try:
            # Convert PCM buffer to WAV format in memory
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(self.CHANNEL)
                wav_file.setsampwidth(2)  # 16-bit PCM
                wav_file.setframerate(self.SAMPLE_RATE)
                wav_file.writeframes(audio_buffer)

            wav_io.seek(0)
            
            # Run transcription in a separate thread
            segments, _ = await asyncio.to_thread(
                self.whisper_model.transcribe,
                wav_io,
                language="en",
                beam_size=5
            )

            # Concatenate transcription segments
            transcription = " ".join(segment.text.strip() for segment in segments)
            
            self.logger.info(f"transcription_success: {transcription}")
            async with aiofiles.open(self.VAD_LOG_FILE, 'a') as f:
                await f.write(f"Transcription: {transcription}\n")
            return transcription

        except Exception as e:
            self.logger.error(f"transcription_error: {e}")
            async with aiofiles.open(self.ERROR_LOG_FILE, 'a') as f:
                await f.write(f"Transcription error: {e}\n")
            return None

    async def capture_until_pause(self):
        """Asynchronously capture audio until a pause, with VAD and transcription."""
        await self.clear_log_files()
        
        self.logger.info("Starting audio stream... Press Ctrl+C to stop")

        stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            channels=self.CHANNEL,
            blocksize=self.BLOCKSIZE,
            callback=self.audio_callback
        )
        
        self.audio_buffer = []
        self.pcm_buffer = []
        self.is_speaking = False
        self.buffer_changed = False
        self.short_silence_transcribed = False
        start_time = time.time()
        max_duration = self.SILENCE_FRAMES * self.FRAME_DURATION

        try:
            await asyncio.to_thread(stream.start)
            
            while True:
                await asyncio.sleep(self.FRAME_DURATION)
                
                # Process log queue
                await self.process_log_queue()
                
                # Check for short silence
                if (self.SHORT_SILENCE_MIN <= self.silence_counter <= self.SHORT_SILENCE_MAX and 
                    self.is_speaking and self.buffer_changed and not self.short_silence_transcribed):
                    self.logger.info("Short silence detected - Queuing for transcription...")
                    audio_array = np.concatenate(self.audio_buffer, axis=0)
                    pcm_buffer = b''.join(self.pcm_buffer)
                    
                    self.buffer_changed = False
                    self.short_silence_transcribed = True
                
                # Check for full pause
                if self.silence_counter >= self.SILENCE_FRAMES and self.is_speaking:
                    self.logger.info("Pause detected")
                    if self.audio_buffer and self.buffer_changed:
                        audio_array = np.concatenate(self.audio_buffer, axis=0)
                        pcm_buffer = b''.join(self.pcm_buffer)
                        transcription = await self.transcribe(pcm_buffer)
                        if transcription:
                            self.transcription = transcription
                            print(f"Transcribed: {transcription}")
                            self.cl_queue.sync_q.put(transcription)
                            return transcription
                        self.segment_counter += 1
                        self.audio_buffer = []
                        self.pcm_buffer = []
                        self.buffer_changed = False
                        self.short_silence_transcribed = False
                    self.is_speaking = False
                
                # Check for timeout
                if time.time() - start_time > self.max_duration:
                    self.callback("timeout")
                    break

        except asyncio.CancelledError:
            self.callback("recording_cancelled")
            print("\nRecording stopped")
            if self.audio_buffer and self.is_speaking:
                audio_array = np.concatenate(self.audio_buffer, axis=0)
                pcm_buffer = b''.join(self.pcm_buffer)
                transcription = await self.transcribe(pcm_buffer)
                if transcription:
                    print(f"Transcribed: {transcription}")
                    self.cl_queue.sync_q.put(transcription)
        
        finally:
            await asyncio.to_thread(stream.stop)
            await asyncio.to_thread(stream.close)
            await self.process_log_queue()  # Process any remaining logs
            print(f"VAD decisions logged to {self.VAD_LOG_FILE}")
            print(f"Errors and timings logged to {self.ERROR_LOG_FILE}")

    async def capture_and_transcribe(self):
        """Capture audio until a pause and transcribe it."""
        return await self.capture_until_pause()
    
    async def wait_for_agent_to_finish(self):
        self.logger.info("⏳ Waiting for agent to finish speaking...")
        self.state = "WAITING_FOR_MESSAGE"
        
        try:
            message = await asyncio.wait_for(self.vad_queue.async_q.get(), timeout=30.0)
            if message == "vad_proceed":
                self.logger.info("🎤 Agent done, capturing vad audio...")
                await self.capture_and_transcribe()
        except asyncio.TimeoutError:
            self.logger.warning("⏰ No message received within 5 seconds.")

    
    async def run(self):
        await self.wait_for_agent_to_finish()
