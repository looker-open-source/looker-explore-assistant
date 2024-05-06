import hmac
import hashlib
import requests
import json

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
    # URL of the endpoint
    url = 'http://localhost:8000'

    # Request payload
    data = {"contents":"how are you doing?", "parameters":{"max_output_tokens": 1000}}

    # Read the secret key from a file
    with open('../.vertex_cf_auth_token', 'r') as file:
        secret_key = file.read().strip()  # Remove any potential newline characters

    # Generate HMAC signature
    signature = generate_hmac_signature(secret_key, data)

    # Send the request
    response = send_request(url, data, signature)
    print("Response from server:", response)

if __name__ == "__main__":
    main()
