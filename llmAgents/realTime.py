import fitz  # PyMuPDF
import json
import websocket
import threading
import time
import os
import pyaudio
import numpy as np

api_key = os.environ.get("OPENAI_API_KEY")

url = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17"
headers = [
    "Authorization: Bearer " + api_key,
    "OpenAI-Beta: realtime=v1"
]

eventID = f"qefwgrg42t3qeff{time.time_ns}"

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

fristTime = True
def on_message(ws, message):
    data = json.loads(message)
    if data["type"] == "response.done":
        print("\nAssistant:", data["message"]["content"])
    elif data["type"] == "response.text.delta":
        if fristTime:
            print("Received event:", json.dumps(data, indent=2))
            fristTime = False
        print(data["message"]["delta"])
    elif data["type"] == "response.text.done":
        play_audio()
    elif data["type"] == "error":
        print("Error:", data["error"]["message"])
    # else:
        # print("Received event:", json.dumps(data, indent=2))

def on_error(ws, error):
    print("Error:", error)

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

def send_user_message(ws, message):
    ws.send(json.dumps({
        "event_id": eventID,
        "type": "response.create",
        "response": {
            "modalities": ["text", 'audio'],
            "instructions": message
        },
    }))

CHUNK = 1024  # size of data chunks for PyAudio
FORMAT = pyaudio.paInt16  # 16-bit PCM
CHANNELS = 1  # Mono
RATE = 16000  # Sample rate (adjust if necessary based on API output)

audio_data = bytearray()
def play_audio():
    global audio_data
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True)

    # Convert bytearray to numpy array for easier chunking
    np_audio = np.frombuffer(audio_data, dtype=np.int16)
    
    # Play the audio in chunks
    for i in range(0, len(np_audio), CHUNK):
        stream.write(np_audio[i:i+CHUNK].tobytes())

    stream.stop_stream()
    stream.close()
    p.terminate()
    audio_data = bytearray() 


def main():
    
    pdf_path = "Lease-Agreement.pdf"
    doc = fitz.open(pdf_path)

    try:
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
        send_user_message(ws, f"Here is the document content: {page.get_text()}. Can you explain what I need to sign?")
        # User interaction loop
        while True:
            user_input = input("You: ")
            if user_input.lower().strip() == 'exit':
                print("Exiting...")
                break
            send_user_message(ws, user_input)

            ws.close()
    except Exception as e:
        print(f"An error occurred: {str(e)}")


if __name__ == "__main__":
    main()
