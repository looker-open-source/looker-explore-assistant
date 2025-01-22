import requests
import json
import os
from dotenv import load_dotenv


load_dotenv()
# Define the endpoint URL
ENDPOINT_URL = "http://localhost:8000/"
OAUTH_TOKEN = os.environ.get("OAUTH_SAMPLE_TOKEN")
if not OAUTH_TOKEN:
    raise ValueError("OAUTH_SAMPLE_TOKEN environment variable is not set")

def send_request():
    # Define the payload to send in the POST request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OAUTH_TOKEN}"
    }
    payload = {
        "contents": "I am testing my query. can you reply HEALTHY?",
        "parameters": {
            "temperature": 0.3,
            "max_output_tokens": 400
        }
    }

    # Send a POST request to the endpoint
    response = requests.post(ENDPOINT_URL, json=payload, headers=headers)

    # Print the response status code and content
    print("Status Code:", response.status_code)
    print("Response Content:", response.text)

if __name__ == "__main__":
    send_request()
