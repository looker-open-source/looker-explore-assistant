import hmac
import hashlib
import requests
import json
import os

secret_key = os.environ.get("VERTEX_CF_AUTH_TOKEN")
url=os.getenv("CLOUDRUN_ENDPOINT")
if not url:
    url = "http://localhost:8000"

def generate_hmac_signature(secret_key, data):
    """
    Generate HMAC-SHA256 signature for the given data using the secret key.
    """
    hmac_obj = hmac.new(secret_key.encode(), json.dumps(data).encode(), hashlib.sha256)
    return hmac_obj.hexdigest()

def send_request(url, data, signature):
    """
    Send a POST request to the given URL with the provided data and HMAC signature.
    """
    headers = {
        'Content-Type': 'application/json',
        'X-Signature': signature
    }
    response = requests.post(url, headers=headers, json=data)
    return response.text

def main():
    print("Sending request to:", url)

    # Request payload
    data = {"contents":"I am just testing if my response works. Can you reply 'HEALTHY'?", "parameters":{"max_output_tokens": 1000}}

    if not secret_key:
        raise ValueError("no VERTEX_CF_AUTH_TOKEN found")
    else:
    # Generate HMAC signature
        signature = generate_hmac_signature(secret_key, data)

    # Send the request
    response = send_request(url, data, signature)
    print("Response from server:", response)

if __name__ == "__main__":
    main()
