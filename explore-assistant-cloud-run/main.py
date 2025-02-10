
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
import logging
import json
import mysql.connector
from flask import Flask, request, Response
from flask_cors import CORS
from datetime import datetime, timezone
from dotenv import load_dotenv; load_dotenv()


from helper_functions import (
    CLOUD_SQL_HOST,
    CLOUD_SQL_USER,
    CLOUD_SQL_PASSWORD,
    CLOUD_SQL_DATABASE,
    IS_DEV_SERVER,
    get_response_headers,
    validate_bearer_token,
    log_request,
    verify_looker_user,
    get_user_from_db,
    create_new_user,
    create_chat_thread,
    add_message,
    add_feedback,
    generate_response,
    record_prompt,
    generate_looker_query,
    validate_bearer_token
)
logging.basicConfig(level=logging.INFO)


# Initialize the Vertex AI
project = os.environ.get("PROJECT")
location = os.environ.get("REGION")
vertex_cf_auth_token = os.environ.get("VERTEX_CF_AUTH_TOKEN")
model_name = os.environ.get("MODEL_NAME", "gemini-1.0-pro-001")
oauth_client_id = os.environ.get("OAUTH_CLIENT_ID")
# checks env var before initiate server
if (
    not project or
    not location or 
    not oauth_client_id
    ):
    raise ValueError("one of environment variables is not set. Please check your delpoyment settings.")


# Flask app for running as a web server
def create_flask_app():
    app = Flask(__name__)
    CORS(app)

    @app.route("/", methods=["POST", "OPTIONS"])
    def base():
        # debug : log down all the calls
        if request.method == "OPTIONS":
            logging.info("Received OPTIONS request")
            return "", 204, get_response_headers()

        incoming_request = request.get_json()
        log_request(incoming_request, 'incoming_request') if IS_DEV_SERVER else None

        logging.info(f"Received POST request with payload: {incoming_request}")
        logging.info(f"Request headers: {dict(request.headers)}")

        contents = incoming_request.get("contents")
        parameters = incoming_request.get("parameters")
        if contents is None:
            logging.warning("Missing 'contents' parameter in request")
            return Response(json.dumps("Missing 'contents' parameter"), 400, headers=get_response_headers(), mimetype='application/json')

        if not validate_bearer_token(request):
            logging.warning("Invalid bearer token detected")
            return Response(json.dumps({"error": "Invalid token"}), 401, headers=get_response_headers(), mimetype='application/json')

        try:
            logging.info(f"Generating Looker query for contents: {contents}")
            response_text = generate_looker_query(contents, parameters)
            log_request(response_text,'vertex_reply__generate_looker_query') if IS_DEV_SERVER else None

            data = [
                {
                    "prompt": contents,
                    "parameters": json.dumps(parameters),
                    "response": response_text,
                    "recorded_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S.$f")
                }
            ]
            record_prompt(data)
            return Response(json.dumps(response_text), 200, headers=get_response_headers(), mimetype='application/json')
        except Exception as e:
            logging.error(f"Internal server error: {str(e)}")
            return Response(json.dumps(str(e)), 500, headers=get_response_headers(), mimetype='application/json')

    @app.route("/login", methods=["POST", "OPTIONS"])
    def login():
        if request.method == "OPTIONS":
            return "", 204, get_response_headers()

        incoming_request = request.get_json()
        if not incoming_request or "user_id" not in incoming_request or "name" not in incoming_request or "email" not in incoming_request:
            return Response(json.dumps({"error": "Missing required parameters"}), 400, headers=get_response_headers(), mimetype='application/json')

        user_id = incoming_request["user_id"]
        name = incoming_request["name"]
        email = incoming_request["email"]

        if not validate_bearer_token(request):
            return Response(json.dumps({"error": "Invalid token"}), 403, headers=get_response_headers(), mimetype='application/json')

        if not verify_looker_user(user_id):
            return Response(json.dumps({"error": "User is not a validated Looker user"}), 403, headers=get_response_headers(), mimetype='application/json')

        user_data = get_user_from_db(user_id)
        if user_data:
            return Response(json.dumps({"message": "User already exists", "user": user_data}), 200, headers=get_response_headers(), mimetype='application/json')

        result = create_new_user(user_id, name, email)
        if "error" in result:  # Check for errors from create_new_user
            return Response(json.dumps(result), 500, headers=get_response_headers(), mimetype='application/json') # Return error details
        return Response(json.dumps({"message": "User created successfully", "user_id": user_id}), 201, headers=get_response_headers(), mimetype='application/json')

    @app.route("/chat", methods=["POST", "OPTIONS"])
    def create_chat():
        if request.method == "OPTIONS":
            return "", 204, get_response_headers()

        if not validate_bearer_token(request):
            return Response(json.dumps({"error": "Invalid token"}), 403, headers=get_response_headers(), mimetype='application/json')

        incoming_request = request.get_json()
        user_id = incoming_request.get("user_id")
        explore_key = incoming_request.get("explore_key")

        if not all([user_id, explore_key]):
            return Response(json.dumps({"error": "Missing required parameters"}), 400, headers=get_response_headers(), mimetype='application/json')

        chat_id = create_chat_thread(user_id, explore_key)

        if chat_id:
            return Response(json.dumps({"chat_id": chat_id, "status": "created"}), 201, headers=get_response_headers(), mimetype='application/json')
        else:
            return Response(json.dumps({"error": "Failed to create chat thread"}), 500, headers=get_response_headers(), mimetype='application/json')

    @app.route("/chat/history", methods=["GET", "OPTIONS"])
    def chat_history():
        if request.method == "OPTIONS":
            return "", 204, get_response_headers()

        user_id = request.args.get("user_id")
        chat_id = request.args.get("chat_id")

        if not all([user_id, chat_id]):
            return Response(json.dumps({"error": "Missing 'user_id' or 'chat_id'"}), 400, headers=get_response_headers(), mimetype='application/json')

        if not validate_bearer_token(request):
            return Response(json.dumps({"error": "Invalid token"}), 403, headers=get_response_headers(), mimetype='application/json')

        try:
            connection = mysql.connector.connect(
                host=CLOUD_SQL_HOST, user=CLOUD_SQL_USER, password=CLOUD_SQL_PASSWORD, database=CLOUD_SQL_DATABASE
            )
            cursor = connection.cursor(dictionary=True)

            query = """
                SELECT m.message_id, m.content, m.is_user_message, m.created_at, f.feedback_text, f.is_positive
                FROM messages m
                LEFT JOIN feedback f ON m.feedback_id = f.feedback_id
                WHERE m.chat_id = %s
                ORDER BY m.created_at ASC
            """  # Join with feedback table
            cursor.execute(query, (chat_id,))
            chat_history_data = cursor.fetchall()

            return Response(json.dumps(chat_history_data), 200, headers=get_response_headers(), mimetype='application/json')

        except mysql.connector.Error as e:
            logging.error(f"Database error in chat_history: {e}")
            return Response(json.dumps({"error": "Failed to retrieve chat history"}), 500, headers=get_response_headers(), mimetype='application/json')

        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()
                
    @app.route("/prompt", methods=["POST", "OPTIONS"])  # Changed to POST
    def handle_prompt():
        if request.method == "OPTIONS":
            return "", 204, get_response_headers()

        if not validate_bearer_token(request):
            return Response(json.dumps({"error": "Invalid token"}), 403, headers=get_response_headers(), mimetype='application/json')

        incoming_request = request.get_json()
        contents = incoming_request.get("contents")  # The prompt content
        parameters = incoming_request.get("parameters")  # Optional parameters
        prompt_type = incoming_request.get("prompt_type")  # Type of prompt (e.g., "looker", "general")
        current_explore_key = incoming_request.get("current_explore_key")
        user_id = incoming_request.get("user_id")
        message = incoming_request.get("message", "") # get the message content

        if not all([contents, prompt_type, current_explore_key, user_id]):
            return Response(json.dumps({"error": "Missing required parameters"}), 400, headers=get_response_headers(), mimetype='application/json')

        if prompt_type == "looker":
            response_text = generate_looker_query(contents, parameters)  # Use generate_looker_query
        else:  # Default to general prompt
            response_text = generate_response(contents, parameters)  # Use generate_response

        chat_id = create_chat_thread(user_id, current_explore_key)  # Create chat thread
        if not chat_id:
            return Response(json.dumps({"error": "Failed to create chat thread"}), 500, headers=get_response_headers(), mimetype='application/json')

        message_id = add_message(chat_id, user_id, message, 1)  # Add user message
        if not message_id:
            return Response(json.dumps({"error": "Failed to add message"}), 500, headers=get_response_headers(), mimetype='application/json')

        message_id = add_message(chat_id, user_id, response_text, 0)  # Add bot message
        if not message_id:
            return Response(json.dumps({"error": "Failed to add message"}), 500, headers=get_response_headers(), mimetype='application/json')

        return Response(json.dumps({"response": response_text, "chat_id": chat_id}), 200, headers=get_response_headers(), mimetype='application/json')

    @app.route("/feedback", methods=["POST", "OPTIONS"])
    def give_feedback():
        if request.method == "OPTIONS":
            return "", 204, get_response_headers()

        if not validate_bearer_token(request):
            return Response(json.dumps({"error": "Invalid token"}), 403, headers=get_response_headers(), mimetype='application/json')

        incoming_request = request.get_json()
        user_id = incoming_request.get("user_id")
        message_id = incoming_request.get("message_id")
        feedback_text = incoming_request.get("feedback_text")
        is_positive = incoming_request.get("is_positive")

        if not all([user_id, message_id, feedback_text, is_positive]):
            return Response(json.dumps({"error": "Missing required parameters"}), 400, headers=get_response_headers(), mimetype='application/json')

        if add_feedback(user_id, message_id, feedback_text, is_positive):
            return Response(json.dumps({"status": "Feedback submitted"}), 200, headers=get_response_headers(), mimetype='application/json')
        else:
            return Response(json.dumps({"error": "Failed to submit feedback"}), 500, headers=get_response_headers(), mimetype='application/json')

    @app.errorhandler(500)
    def internal_server_error(error):
        return Response(
            json.dumps({"error": "Internal server error"}),
            status=500,
            mimetype="application/json",
            headers=get_response_headers()
        )

    return app


# Determine the running environment and execute accordingly
if __name__ == "__main__":
    app = create_flask_app()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
