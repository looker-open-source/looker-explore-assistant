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
from flask import Flask, request
from flask_cors import CORS, cross_origin
import vertexai
from urllib.parse import urlparse, parse_qs
import json
import re

app = Flask(__name__)
CORS(app)

# instantiate gemini model for prediction
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
model = GenerativeModel("gemini-pro")


@app.route("/", methods = ["POST"])
def looker_llm_vis():
    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600"
        }

        return ("", 204, headers)
    
    
    project = os.environ.get("PROJECT")
    location = os.environ.get("REGION")

    vertexai.init(project=project, location=location)
    parameters = {
        "temperature": 0.2,
        "max_output_tokens": 2000,### Reduce token to avoid having multiples results on the same request
        "top_p": 0.8,
        "top_k": 40
    }

    context = """You\'re a developer who would transalate questions to a structured URL query based on the following json of fields - choose only the fields in the below description using the field "name" in the url. Make sure a limit of 500 or less is always applied.: \n
    """

    # read examples jsonl file from local filesystem
    # in a production use case, reading from cloud storage would be recommended
    incoming_request = request.get_json()
    examples = """\n The examples here showcase how the url should be constructed. Only use the "dimensions" and "measures" above for fields, filters and sorts: \n"""
    with open(f"./{incoming_request['model']}::{incoming_request['explore']}.jsonl","r") as f:
        lines = f.readlines()

        for line in lines:
            print(f"input: {json.loads(line)['input']} \n output: {json.loads(line)['output']} \n")
            examples += (f"input: {json.loads(line)['input']}\n output: {json.loads(line)['output']}\n")

    
    if incoming_request and 'question' in incoming_request:
        llm = """
            input: {}
            output: """.format(incoming_request['question']) ### Formating our input to the model
        predict = context
        
        # read lookml metadata file, append to prompt
        with open(f"./{incoming_request['model']}::{incoming_request['explore']}.txt", "r") as metadata_file:
            predict += metadata_file.read()
        
        # build examples into prompt
        predict += examples + llm

        # make prediction to generate Looker Explore URL
        response =  model.generate_content(
            contents=predict,
            generation_config=GenerationConfig(
                temperature=0.2,
                top_p=0.8,
                top_k=40,
                max_output_tokens=1000,
                candidate_count=1
            )
        )

        # grab token character count metadata and log
        metadata = response.__dict__['_raw_response'].usage_metadata
        # print({"request": request_json['question'],"response": response.text, "input_characters": metadata.prompt_token_count, "output_characters": metadata.candidates_token_count})

        # Complete a structured log entry.
        entry = dict(
            severity="INFO",
            message={"model":incoming_request['model'],"explore":incoming_request['explore'],"request": incoming_request['question'],"response": response.text, "input_characters": metadata.prompt_token_count, "output_characters": metadata.candidates_token_count},
            # Log viewer accesses 'component' as jsonPayload.component'.
            component="explore-assistant-metadata",
        )

        print(json.dumps(entry))
        

        # Set CORS headers for extension request
        headers = {
            "Access-Control-Allow-Origin": "*"
        }

        return (f"{response.text.rstrip().lstrip()}&toggle=dat,pik,vis",200,headers)
    else:
        return ('Bad Request',400)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))