
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
import json
from flask import Flask, request
from flask_cors import CORS, cross_origin
import functions_framework
import vertexai
from urllib.parse import urlparse, parse_qs

# Initialize the Vertex AI
project = os.environ.get("PROJECT")
location = os.environ.get("REGION")
vertexai.init(project=project, location=location)

def generate_looker_query(request_json, explore_file):

    parameters = {
        "temperature": 0.2,
        "max_output_tokens": 100,### Reduce token to avoid having multiples results on the same request
        "top_p": 0.8,
        "top_k": 40
    }

    context = """You\'re a developer who would transalate questions to a structured URL query based on the following json of fields - choose only the fields in the below description using the field "name" in the url. Make sure a limit of 500 or less is always applied.: \n
    """

    # read examples jsonl file from local filesystem
    # in a production use case, reading from cloud storage would be recommended
    examples = """\n The examples here showcase how the url should be constructed. Only use the "dimensions" and "measures" above for fields, filters and sorts: \n"""

    with open("./examples.jsonl", "r") as f:
        lines = f.readlines()

        for line in lines:
            examples += (f"input: {json.loads(line)['input']} \n" + f"output: {json.loads(line)['output']} \n") 



    if request_json and 'question' in request_json:
        llm = """
            input: {}
            output: """.format(request_json['question']) ### Formating our input to the model
        predict = context + request_json['explore'] + examples + llm

        # instantiate gemini model for prediction
        from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
        model = GenerativeModel("gemini-pro")

        # make prediction to generate Looker Explore URL
        response =  model.generate_content(
            contents=predict,
            generation_config=GenerationConfig(
                temperature=0.2,
                top_p=0.8,
                top_k=40,
                max_output_tokens=100,
                candidate_count=1
            )
        )

        # grab token character count metadata and log
        metadata = response.__dict__['_raw_response'].usage_metadata

        # Complete a structured log entry.
        entry = dict(
            severity="INFO",
            message={"request": request_json['question'],"response": response.text, "input_characters": metadata.prompt_token_count, "output_characters": metadata.candidates_token_count},
            # Log viewer accesses 'component' as jsonPayload.component'.
            component="explore-assistant-metadata",
        )

        print(json.dumps(entry))
        


# Flask app for running as a web server
def create_flask_app():
    app = Flask(__name__)
    CORS(app)

    @app.route("/", methods=["POST", "OPTIONS"])
    def base():
        if request.method == "OPTIONS":
            return handle_options_request()
        
        incoming_request = request.get_json()
        explore_file = f"./{incoming_request['model']}::{incoming_request['explore']}.jsonl"
        response_text = generate_looker_query(incoming_request, explore_file)
        
        # Set CORS headers for the actual request
        headers = {"Access-Control-Allow-Origin": "*"}
        return response_text, 200, headers

    return app


# Function for Google Cloud Function
@functions_framework.http
def cloud_function_entrypoint(request):
    if request.method == "OPTIONS":
        return handle_options_request()

    request_json = request.get_json(silent=True)
    explore_file = "./examples.jsonl"
    response_text = generate_looker_query(request_json, explore_file)

    # Set CORS headers for the actual request
    headers = {"Access-Control-Allow-Origin": "*"}
    return response_text, 200, headers

def handle_options_request():
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "3600"
    }
    return "", 204, headers


# Determine the running environment and execute accordingly
if __name__ == "__main__":
    # Detect if running in a Google Cloud Function environment
    if os.environ.get("FUNCTIONS_FRAMEWORK"):
        # The Cloud Function entry point is defined by the decorator, so nothing is needed here
        pass
    else:
        app = create_flask_app()
        app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))