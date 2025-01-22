
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
import functions_framework
import vertexai
import logging
import json

from google.cloud import bigquery
from datetime import datetime, timezone
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from flask import Flask, request, Response
from flask_cors import CORS
import requests


logging.basicConfig(level=logging.INFO)


# Initialize the Vertex AI
project = os.environ.get("PROJECT_NAME")
location = os.environ.get("REGION_NAME")
model_name = os.environ.get("MODEL_NAME", "gemini-1.0-pro-001")
oauth_client_id = os.environ.get("OAUTH_CLIENT_ID")
# checks env var before initiate server
if (
    not project or
    not location or 
    not oauth_client_id
    ):
    raise ValueError("one of environment variables is not set. Please check your delpoyment settings.")

vertexai.init(project=project, location=location)

def get_response_headers(request):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
    return headers



def validate_bearer_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        logging.error("Missing or malformed Authorization header")
        return False

    token = auth_header.split(' ')[1]
    try:
        # Validate access token using Google's tokeninfo endpoint
        response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?access_token={token}')

        if response.status_code == 200:
            token_info = response.json()
            # Verify the token was issued for our client ID
            expected_client_id = oauth_client_id
            if token_info.get('azp') != expected_client_id:
                logging.error(f"Token was issued for different client ID: {token_info.get('azp')}")
                return False

            logging.info(f"Token verification successful. Info: {token_info}")
            return True

        logging.error(f"Token validation failed with status code: {response.status_code}")
        logging.error(f"Response content: {response.text}")
        return False

    except Exception as e:
        logging.error(f"Token validation failed with unexpected error: {str(e)}")
        return False

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
        # message={"request": contents, "response": response.text,
        #          "input_characters": metadata.prompt_token_count, "output_characters": metadata.candidates_token_count},
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
            logging.info("Received OPTIONS request")
            return handle_options_request(request)

        incoming_request = request.get_json()
        logging.info(f"Received POST request with payload: {incoming_request}")
        logging.info(f"Request headers: {dict(request.headers)}")

        contents = incoming_request.get("contents")
        parameters = incoming_request.get("parameters")
        if contents is None:
            logging.warning("Missing 'contents' parameter in request")
            return "Missing 'contents' parameter", 400, get_response_headers(request)

        if not validate_bearer_token(request):
            logging.warning("Invalid bearer token detected")
            return "Invalid token", 401, get_response_headers(request)

        try:
            logging.info(f"Generating Looker query for contents: {contents}")
            response_text = generate_looker_query(contents, parameters)
            data = [
                {
                    "prompt": contents,
                    "parameters": json.dumps(parameters),
                    "response": response_text,
                    "recorded_at": datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S.%f")
                }
            ]
            record_prompt(data)
            return response_text, 200, get_response_headers(request)
        except Exception as e:
            logging.error(f"Internal server error: {str(e)}")
            return str(e), 500, get_response_headers(request)


    @app.errorhandler(500)
    def internal_server_error(error):
        return "Internal server error", 500, get_response_headers(request)

    return app


def record_prompt(data):
    client = bigquery.Client()
    job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        )
    destination = "joon-sandbox.beck_explore_assistant._prompts"
    load_job = client.load_table_from_json(
        json_rows=data,
        job_config=job_config,
        destination=destination)
    print(f"Load job sent.")
    load_job.result()  # Waits for the job to complete.
    print(f"Loaded {load_job.output_rows} prompt into {destination} BQ table")


# Function for Google Cloud Function
@functions_framework.http
def cloud_function_entrypoint(request):
    if request.method == "OPTIONS":
        return handle_options_request(request)

    incoming_request = request.get_json()
    print(incoming_request)
    contents = incoming_request.get("contents")
    parameters = incoming_request.get("parameters")
    if contents is None:
        return "Missing 'contents' parameter", 400, get_response_headers(request)


    try:
        response_text = generate_looker_query(contents, parameters)
        data = [
            {
                "prompt": contents,
                "parameters": json.dumps(parameters),
                "response": response_text,
                "recorded_at": datetime.now(timezone.utc).strftime("%Y/%m/%d %H:%M:%S.%f")
            }
        ]
        record_prompt(data)
        return response_text, 200, get_response_headers(request)
    except Exception as e:
        logging.error(f"Internal server error: {str(e)}")
        return str(e), 500, get_response_headers(request)


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
