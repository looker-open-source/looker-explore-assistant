
# MIT License

# Copyright (c) 2023 Looker Data Sciences, Inc.

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import hmac
from flask import Flask, request, Response
from flask_cors import CORS
import functions_framework
import vertexai
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
import logging

logging.basicConfig(level=logging.INFO)


# Initialize the Vertex AI
project = os.environ.get("PROJECT")
location = os.environ.get("REGION")
vertex_cf_auth_token = os.environ.get("VERTEX_CF_AUTH_TOKEN")
model_name = os.environ.get("MODEL_NAME", "gemini-1.0-pro-001")

vertexai.init(project=project, location=location)

def get_response_headers(request):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Signature"
    }
    return headers


def has_valid_signature(request):
    signature = request.headers.get("X-Signature")
    if signature is None:
        return False

    # Validate the signature
    secret = vertex_cf_auth_token.encode("utf-8")
    request_data = request.get_data()
    hmac_obj = hmac.new(secret, request_data, "sha256")
    expected_signature = hmac_obj.hexdigest()

    return hmac.compare_digest(signature, expected_signature)

def generate_looker_query(contents, parameters=None, model_name="gemini-1.5-flash"):

   # Define default parameters
    default_parameters = {
        "temperature": 0.2,
        "max_output_tokens": 500,
        "top_p": 0.8,
        "top_k": 40
    }

    # Override default parameters with any provided in the request
    if parameters:
        default_parameters.update(parameters)

    # instantiate gemini model for prediction
    model = GenerativeModel(model_name)

    # make prediction to generate Looker Explore URL
    response = model.generate_content(
        contents=contents,
        generation_config=GenerationConfig(
            temperature=default_parameters["temperature"],
            top_p=default_parameters["top_p"],
            top_k=default_parameters["top_k"],
            max_output_tokens=default_parameters["max_output_tokens"],
            candidate_count=1
        )
    )

    # grab token character count metadata and log
    metadata = response.__dict__['_raw_response'].usage_metadata

    # Complete a structured log entry.
    entry = dict(
        severity="INFO",
        message={"request": contents, "response": response.text,
                 "input_characters": metadata.prompt_token_count, "output_characters": metadata.candidates_token_count},
        # Log viewer accesses 'component' as jsonPayload.component'.
        component="explore-assistant-metadata",
    )
    logging.info(entry)
    return response.text


# Flask app for running as a web server
def create_flask_app():
    app = Flask(__name__)
    CORS(app)

    @app.route("/", methods=["POST", "OPTIONS"])
    def base():
        if request.method == "OPTIONS":
            return handle_options_request(request)

        incoming_request = request.get_json()
        print(incoming_request)
        contents = incoming_request.get("contents")
        parameters = incoming_request.get("parameters")
        if contents is None:
            return "Missing 'contents' parameter", 400

        if not has_valid_signature(request):
            return "Invalid signature", 403

        response_text = generate_looker_query(contents, parameters)

        return response_text, 200, get_response_headers(request)

    return app


# Function for Google Cloud Function
@functions_framework.http
def cloud_function_entrypoint(request):
    if request.method == "OPTIONS":
        return handle_options_request(request)

    incoming_request = request.get_json()
    contents = incoming_request.get("contents")
    parameters = incoming_request.get("parameters")
    if contents is None:
        return "Missing 'contents' parameter", 400

    response_text = generate_looker_query(contents, parameters)

    return response_text, 200, get_response_headers(request)


def handle_options_request(request):
    return "", 204, get_response_headers(request)


# Determine the running environment and execute accordingly
if __name__ == "__main__":
    # Detect if running in a Google Cloud Function environment
    if os.environ.get("FUNCTIONS_FRAMEWORK"):
        # The Cloud Function entry point is defined by the decorator, so nothing is needed here
        pass
    else:
        app = create_flask_app()
        app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
