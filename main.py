import os
import time
import requests
import simpleaudio as sa
from pydub import AudioSegment
from io import BytesIO

# Set up your OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
    "OpenAI-Beta": "assistants=v1",
}

# Base URL for OpenAI API
base_url = "https://api.openai.com/v1"


# Function to get the assistant's latest response from the messages
def get_assistants_latest_response(messages):
    # Filter out messages by the assistant
    assistant_messages = sorted(
        [msg for msg in messages if msg["role"] == "assistant"],
        key=lambda x: x["created_at"],
    )
    if assistant_messages:
        # Assuming the last message from the assistant is the response we want
        return assistant_messages[-1]["content"][0]["text"]["value"]
    return "No response found."


# Function to list messages in a thread
def list_messages_in_thread(thread_id):
    url = f"{base_url}/threads/{thread_id}/messages"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to list messages in thread: {response.text}")


# Function to retrieve a run
def retrieve_run(thread_id, run_id):
    url = f"{base_url}/threads/{thread_id}/runs/{run_id}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to retrieve run: {response.text}")


# Function to poll for the run completion
def poll_run_until_complete(thread_id, run_id):
    while True:
        run = retrieve_run(thread_id, run_id)
        status = run.get("status")
        if status == "completed":
            return run
        elif status in ["failed", "cancelled"]:
            raise Exception(f"Run failed or was cancelled: {run}")
        time.sleep(1)  # Sleep for a short period before polling again


# Function to create an assistant
def create_assistant():
    url = f"{base_url}/assistants"
    data = {
        "model": "gpt-4-1106-preview",
        "instructions": "You are a helpful assistant.",
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()


# Function to create a thread
def create_thread():
    url = f"{base_url}/threads"
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Failed to create thread: {response.text}")


def add_message_to_thread(thread_id, content, role="user"):
    url = f"{base_url}/threads/{thread_id}/messages"
    data = {"role": role, "content": content}
    response = requests.post(url, json=data, headers=headers)
    return response.json()


# Function to run the assistant
def run_assistant(thread_id, assistant_id):
    url = f"{base_url}/threads/{thread_id}/runs"
    data = {"assistant_id": assistant_id}
    response = requests.post(url, json=data, headers=headers)
    return response.json()


# Function to generate speech from text
def generate_speech(text):
    url = f"{base_url}/audio/speech"
    data = {"model": "tts-1", "input": text, "voice": "alloy", "response_format": "mp3"}
    response = requests.post(url, json=data, headers=headers)
    return response.content


# Function to play audio
def play_audio(audio_content):
    audio = AudioSegment.from_file(BytesIO(audio_content), format="mp3")
    playback = sa.play_buffer(
        audio.raw_data,
        num_channels=audio.channels,
        bytes_per_sample=audio.sample_width,
        sample_rate=audio.frame_rate,
    )
    playback.wait_done()


# Main function to start the assistant thread and handle continuous interaction
def start_assistant():
    assistant = create_assistant()
    thread = create_thread()
    thread_id = thread["id"]  # Extract the thread ID

    while True:
        user_input = input(
            "Enter your question for the assistant (or type 'exit' to quit): "
        )
        if user_input.lower() == "exit":
            break

        add_message_to_thread(thread_id, user_input)
        run_response = run_assistant(thread_id, assistant["id"])
        run_id = run_response["id"]  # Extract the run ID

        # Poll for the run to complete
        poll_run_until_complete(thread_id, run_id)

        # Now retrieve the messages from the thread
        messages_response = list_messages_in_thread(thread_id)
        messages = messages_response.get("data", [])

        # Get the assistant's latest response
        assistant_response = get_assistants_latest_response(messages)
        print(f"Assistant's response: {assistant_response}")

        # Generate and play speech
        audio_response = generate_speech(assistant_response)
        play_audio(audio_response)


if __name__ == "__main__":
    start_assistant()
