from TTS.api import TTS
import os
from chatterly.utils.log_exec_time import LogExecutionTime

@LogExecutionTime(label="Loading Xttsv2 model")
def load_model():
    # Load XTTSv2 model
    tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
    tts.to("cuda")
    return tts 

@LogExecutionTime(label="Generate Cloned Voice")
def gen_voice(tts, text: str, reference_audio_path: str, output_path: str = "output.wav", language: str = "en"):
    # Generate speech with cloning
    tts.tts_to_file(
        text=text,
        speaker_wav=reference_audio_path,
        language=language,
        file_path=output_path
    )

    return output_path

def generate_speech_xttsv2(text: str, reference_audio_path: str, output_path: str = "output.wav", language: str = "en"):
    """
    Generate speech using XTTSv2 with voice cloning from a reference audio.

    Args:
        text (str): The input text to synthesize.
        reference_audio_path (str): Path to the reference audio file for cloning.
        output_path (str): Path to save the generated speech.
        language (str): Language code (e.g., "en", "fr", "de").

    Returns:
        str: Path to the generated audio file.
    """
    
    tts = load_model()
    # Generate speech with cloning
    output_path = gen_voice(tts,text,reference_audio_path,output_path,language)

    return output_path
