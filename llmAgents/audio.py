import pyaudio
import wave
import numpy as np
import time

# Define the path to your WAV file
filename = '/Users/Adrian/Projects/DocuSign2/data/dog.wav'
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = '/Users/Adrian/Projects/DocuSign2/data/output.wav'

def record():
    # Initialize PyAudio
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* recording")

    frames = []

    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("* done recording")

    # Stop and close the stream 
    stream.stop_stream()
    stream.close()
    p.terminate()

    # Save the recorded data as a WAV file
    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

print(f"Audio file saved as {WAVE_OUTPUT_FILENAME}")

def play(filename):
    # Open the WAV file
    wf = wave.open(filename, 'rb')

    # Instantiate PyAudio
    p = pyaudio.PyAudio()

    # Open a stream with the same parameters as the WAV file
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)

    # Read data in chunks
    data = wf.readframes(1024)

    # Play the audio by writing data to the stream
    while data:
        stream.write(data)
        data = wf.readframes(1024)

    # Cleanup
    stream.stop_stream()
    stream.close()
    p.terminate()

def main():
    record()
    play(WAVE_OUTPUT_FILENAME)

if __name__ == '__main__':
    main()
