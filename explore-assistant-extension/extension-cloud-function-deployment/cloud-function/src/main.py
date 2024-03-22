
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


import functions_framework
import vertexai
import os
from urllib.parse import urlparse, parse_qs
import json
import re

@functions_framework.http
def gen_looker_query(request):
    """
    Generate Looker query based on the given request.

    Args:
        request (flask.Request): The HTTP request object.

    Returns:
        tuple: A tuple containing the response body, status code, and headers.
    """

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
        "max_output_tokens": 100,### Reduce token to avoid having multiples results on the same request
        "top_p": 0.8,
        "top_k": 40
    }

    context = """You\'re a developer who would transalate questions to a structured URL query based on the following json of fields - choose only the fields in the below description using the field "name" in the url. Make sure a limit of 500 or less is always applied.: \n
    """

    # read examples jsonl file from local filesystem
    # in a production use case, reading from cloud storage would be recommended
    examples = """\n The examples here showcase how the url should be constructed. Only use the "dimensions" and "measures" above for fields, filters and sorts: \n"""

    request_json = request.get_json(silent=True)

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
        

        # Set CORS headers for extension request
        headers = {
            "Access-Control-Allow-Origin": "*"
        }

        print("Response: ", response.text, "Headers: ", headers)

        return (response.text,200,headers)
    else:
        return ('Bad Request',400)