import hmac
import hashlib
import requests
import json

def send_request(url, data):
    """
    Send a POST request to the given URL with the provided data.
    """
    headers = {
        'Content-Type': 'application/json',
    }
    response = requests.post(url, headers=headers, json=data)
    return response.text

def main():
    # URL of the endpoint
    url = 'http://localhost:8000'

    # Request payload
    data = {
        "contents": "how are you doing?",
        "parameters": {"max_output_tokens": 1000},
        "client_secret": None  # Placeholder for client secret
    }

    # Read the secret key from a file
    with open('../.vertex_cf_auth_token', 'r') as file:
        secret_key = file.read().strip()  # Remove any potential newline characters

    # Set the client secret in the payload
    data["client_secret"] = secret_key

    # Send the request
    response = send_request(url, data)
    print("Response from server:", response)

if __name__ == "__main__":
    main()
