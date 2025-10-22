import os
import requests

def generate_playai_tts(text: str, output_path: str = "./samples/playai_output.wav"):
    """
    Generate speech using PlayAI Dialog v1.0 TTS API.

    Args:
        text (str): Input text to synthesize.
        output_path (str): Path to save the generated audio.

    Returns:
        str: Path to the saved audio file.
    """
    import os
    from groq import Groq

    client = Groq(api_key="<key>")

    speech_file_path = "speech.wav" 
    model = "playai-tts"
    voice = "Fritz-PlayAI"
    text = "I love building and shipping new features for our users!"
    response_format = "wav"

    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format=response_format
    )

    response.write_to_file(speech_file_path)