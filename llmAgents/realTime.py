import fitz  # PyMuPDF
import json
import websocket
import threading
import time
import os
import pyaudio
import base64
import wave
import numpy as np

api_key = os.environ.get("OPENAI_API_KEY")

url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
pdf_path = '/Users/Adrian/Projects/DocuSign2/data/Lease-Agreement.docx'
user_audio_filename = '/Users/Adrian/Projects/DocuSign2/data/userAudioMsg.wav'
agent_audio_filename = '/Users/Adrian/Projects/DocuSign2/data/AgentAudioMsg.wav'

headers = [
    "Authorization: Bearer " + api_key,
    "OpenAI-Beta: realtime=v1"
]

eventID = ''

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5
SAMPLESIZE = None

audio_chunks = []
audio_lock = threading.Lock()  # To safely add to audio_chunks from different threads


def play_audio():
    global audio_chunks
    
    # Combine all chunks
    with audio_lock:
        full_audio = b''.join(audio_chunks)
        audio_chunks = []  # Clear for the next recording
    
    # Play audio
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True)

    # Write audio data to stream
    stream.write(full_audio)
    
    # Cleanup
    stream.stop_stream()
    stream.close()
    p.terminate()

def save_audio(filename, frames):
    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(SAMPLESIZE)
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def on_open(ws):
    print("Connected to server.")
    # Initiate session with model
    ws.send(json.dumps({
        "event_id": eventID,
        "type": "session.update",
        "session": {
            "modalities": ["text"],
            "instructions": "You are a helpful assistant."
        },
    }))

def on_message(ws, message):
    global audio_chunks
    
    data = json.loads(message)

    if data['type'] == 'response.audio_transcript.delta':
        print(data['delta'], end=' ')
    elif data['type'] == 'response.audio_transcript.done':
        print(data['transcript'])
    
    elif data['type'] == 'response.audio.delta':
        with audio_lock:
            audio_chunks.append(base64.b64decode(data['delta']))
    elif data['type'] == 'response.audio.done':
        save_audio(agent_audio_filename, audio_chunks)
        play_audio()
    
    elif data["type"] == "response.text.delta":
       print(data['delta'], end=' ')
    elif data["type"] == "response.text.done":
        pass
    
    elif data["type"] == "error":
        print("Error:", data["error"]["message"])
    elif data["type"] == "error":
        global eventID
        eventID = data['event_id']
    else:
        print(data["type"])

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

def send_user_message(ws, message):
    ws.send(json.dumps({
        # "event_id": eventID,
        "type": "response.create",
        "response": {
            "modalities": ["text", 'audio'],
            "instructions": message
        },
    }))

def send_user_audio(ws, audio):
    ws.send(json.dumps({
        # "event_id": eventID,
        "type": "input_audio_buffer.append",
        "audio": audio
    }))
    
def send_user_audio_commit(ws, id):
    ws.send(json.dumps({
        "event_id": id,
        "type": "input_audio_buffer.commit"
    }))

def main():
    doc = fitz.open(pdf_path)
    page = doc[0]
    ws = websocket.WebSocketApp(
        url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # Start the WebSocket connection
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    time.sleep(2)
    # send_user_message(ws, f"Here is the document content: {page.get_text()}. Can you explain what I need to sign?")
    # time.sleep(5)

    p = pyaudio.PyAudio()
    global SAMPLESIZE
    SAMPLESIZE = p.get_sample_size(FORMAT)

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    frames = []
    print("* recording")
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    audio_base64 = base64.b64encode(b''.join(frames)).decode('utf-8')

    # print("Send audio chunk:", json.dumps(payload, indent=2))
    send_user_audio(ws, audio_base64)

    print("* done recording")
    save_audio(user_audio_filename, frames)

    # Stop and close the stream 
    stream.stop_stream()
    stream.close()
    p.terminate()

    send_user_message(ws, f"Here is the document content: {page.get_text()}. Can you explain what I need to sign?")
    
    _ = input('Press any key to exit: ')

    # Sleep 5s to receive all  messages form the 
    time.sleep(5)

    ws.close()


if __name__ == "__main__":
    main()
