import os
import json
import sounddevice as sd
from scipy.io.wavfile import write
import wavio as wv
from io import BytesIO, FileIO
from openai import OpenAI
import datetime
from pydub import AudioSegment
from pydub.playback import play


openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)


def get_audio_instruction(duration=5):
    # Sampling frequency
    freq = 44100
    
    # Recording duration
    # duration = 5
    
    # Start recorder with the given values 
    # of duration and sample frequency
    recording = sd.rec(int(duration * freq), samplerate=freq, channels=1)
    
    print("Start recording...")
    # Record audio for the given number of seconds
    sd.wait()
    print("End recording...")
    
    byte_stream = BytesIO()
    wv.write(byte_stream, recording, freq, sampwidth=2)

    return byte_stream


def transcribe(byte_stream):
    start = datetime.datetime.now()
    byte_stream.seek(0)
    audio_file = ("audio.wav", byte_stream, "audio/wav")  # ("audio.wav", buffer, "audio/wav")
    
    # prompt = "This audio is that of an employee contacting the service agent Barista for assistance. Please transcribe the audio and translate it into english."
    # prompt = "This audio is that of an employee contacting the service agent Barista for assistance. Please transcribe the audio."
    prompt = "The audio is an instruction to a device. Transcribe the audio and translate it into english."
    
    start = datetime.datetime.now()
    transcription = client.audio.transcriptions.create(
        file=audio_file,
        # model="whisper-1",
        model="gpt-4o-mini-transcribe",
        prompt=prompt,
    )
    secs = (datetime.datetime.now() - start).total_seconds()
    print(f"Time for transcription: {secs} secs")
    # print(transcription.words)
    # print(transcription.text)
    return transcription.text


def write_response_to_stream(response, byte_stream):
    chunks: list[bytes] = []
    for chunk in response.iter_bytes(chunk_size=1024):
        if chunk:
            chunks.append(chunk)
    audio_bytes = b"".join(chunks)
    byte_stream.write(audio_bytes)
    

def text_to_speech(
    text, model="gpt-4o-mini-tts", voice="coral", 
    instructions="Speak as an assistant in a sincere tone."
):
    byte_stream = BytesIO()
    start = datetime.datetime.now()
    with client.audio.speech.with_streaming_response.create(
        model=model, voice=voice, input=text, instructions=instructions
    ) as response:
        # response.stream_to_file(speech_file_path)
        write_response_to_stream(response, byte_stream)
    secs = (datetime.datetime.now() - start).total_seconds()
    print(f"Time for text-to-speech: {secs} secs")
    return byte_stream


# Function to play audio from byte stream
def play_audio_from_bytes(byte_stream, volume=40):
    audio = AudioSegment.from_file(byte_stream, format="mp3")
    play(audio + volume)


def speak(text, volume=40):
    byte_stream = text_to_speech(text)
    byte_stream.seek(0)
    play_audio_from_bytes(byte_stream, volume=volume)
    byte_stream.seek(0)
    return byte_stream
