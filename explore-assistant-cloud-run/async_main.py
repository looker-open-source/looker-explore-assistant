import os
import logging
import json
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from helper_functions import (
    IS_DEV_SERVER,
    validate_bearer_token,
    log_request,
    verify_looker_user,
    get_user_from_db,
    create_new_user,
    create_chat_thread,
    retrieve_chat_history,
    add_message,
    add_feedback,
    generate_response,
    record_prompt,
    generate_looker_query,
    DatabaseError,
    search_chat_history
)

logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/")
async def base(request: Request):
    incoming_request = await request.json()
    log_request(incoming_request, 'incoming_request') if IS_DEV_SERVER else None

    if "contents" not in incoming_request:
        raise HTTPException(status_code=400, detail="Missing 'contents' parameter")

    if not validate_bearer_token(request):
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        contents = incoming_request["contents"]
        parameters = incoming_request.get("parameters")
        
        response_text = generate_looker_query(contents, parameters)
        log_request(response_text, 'vertex_reply__generate_looker_query') if IS_DEV_SERVER else None

        data = [{
            "prompt": contents,
            "parameters": json.dumps(parameters),
            "response": response_text,
            "recorded_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S.$f")
        }]
        record_prompt(data)
        
        return {"data": response_text}
    except TimeoutError:
        raise HTTPException(
            status_code=500,
            detail="Request timed out. Please try again."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
async def login(request: Request):
    incoming_request = await request.json()
    if not incoming_request or "user_id" not in incoming_request or "name" not in incoming_request or "email" not in incoming_request:
        raise HTTPException(status_code=400, detail="Missing required parameters")

    user_id = incoming_request["user_id"]
    name = incoming_request["name"]
    email = incoming_request["email"]

    if not validate_bearer_token(request):
        raise HTTPException(status_code=403, detail="Invalid token")

    if not verify_looker_user(user_id):
        raise HTTPException(status_code=403, detail="User is not a validated Looker user")
    
    # catch any cloudSQL errors
    try: 
        user_data = get_user_from_db(user_id)
        if user_data:
            return {"message": "User already exists", "data": user_data}

        result = create_new_user(user_id, name, email)
        
        data = result
        return {"message": "User created successfully", "data": data}
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})

@app.post("/chat")
async def create_chat(request: Request):
    incoming_request = await request.json()
    if not incoming_request or "user_id" not in incoming_request or "explore_key" not in incoming_request:
        raise HTTPException(status_code=400, detail="Missing required parameters")

    if not validate_bearer_token(request):
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        user_id = incoming_request["user_id"]
        explore_key = incoming_request["explore_key"]
        
        if not all([user_id, explore_key]):
            return HTTPException(status_code=400, detail="Missing required parameters")

        chat_id = create_chat_thread(user_id, explore_key)
        if not chat_id:
            raise HTTPException(status_code=500, detail="Failed to create chat thread")
            
        return {"message": "Chat created successfully", "data": {"chat_id": chat_id, "status": "created"}}
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})

@app.get("/chat/history")
async def chat_history(request: Request, user_id: str, chat_id: str):
    if not user_id or not chat_id:
        raise HTTPException(status_code=400, detail="Missing 'user_id' or 'chat_id'")

    if not validate_bearer_token(request):
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        chat_history_data = retrieve_chat_history(chat_id)
        if not chat_history_data or not chat_history_data.get("data"):
            raise HTTPException(status_code=404, detail="Chat history not found")
        return chat_history_data
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})

@app.post("/prompt")
async def handle_prompt(request: Request):
    incoming_request = await request.json()
    required_fields = ["contents", "prompt_type", "current_explore_key", "user_id"]
    if not all(field in incoming_request for field in required_fields):
        raise HTTPException(status_code=400, detail="Missing required parameters")

    if not validate_bearer_token(request):
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        contents = incoming_request["contents"]
        parameters = incoming_request.get("parameters")
        prompt_type = incoming_request["prompt_type"]
        current_explore_key = incoming_request["current_explore_key"]
        user_id = incoming_request["user_id"]
        message = incoming_request.get("message", "")

        # Generate response based on prompt type
        response_text = generate_looker_query(contents, parameters) if prompt_type == "looker" else generate_response(contents, parameters)

        # Create chat thread and add messages
        chat_id = create_chat_thread(user_id, current_explore_key)
        if not chat_id:
            raise HTTPException(status_code=500, detail="Failed to create chat thread")

        # Add user message
        user_message_id = add_message(chat_id, user_id, message, 1)
        if not user_message_id:
            raise HTTPException(status_code=500, detail="Failed to add user message")

        # Add bot message
        bot_message_id = add_message(chat_id, user_id, response_text, 0)
        if not bot_message_id:
            raise HTTPException(status_code=500, detail="Failed to add bot message")

        return {"message": "Prompt handled successfully", "data": {"response": response_text, "chat_id": chat_id}}
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def give_feedback(request: Request):
    incoming_request = await request.json()
    required_fields = ["user_id", "message_id", "feedback_text", "is_positive"]
    if not all(field in incoming_request for field in required_fields):
        raise HTTPException(status_code=400, detail="Missing required parameters")

    if not validate_bearer_token(request):
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        user_id = incoming_request["user_id"]
        message_id = incoming_request["message_id"]
        feedback_text = incoming_request["feedback_text"]
        is_positive = incoming_request["is_positive"]

        result = add_feedback(user_id, message_id, feedback_text, is_positive)
        if result:
            return {"message": "Feedback submitted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to submit feedback")
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})

@app.get("/chat/search")
async def search_chats(request: Request):
    """
    Search through chat history for messages containing specific keywords.
    Returns entire chats that contain matching messages.
    """
    # Get query parameters from request
    params = request.query_params
    user_id = params.get("user_id")
    search_query = params.get("search_query")
    limit = int(params.get("limit", 10))
    offset = int(params.get("offset", 0))

    if not validate_bearer_token(request):
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        if not user_id or not search_query:
            raise HTTPException(status_code=400, detail="Missing required parameters")

        search_results = search_chat_history(
            user_id=user_id,
            search_query=search_query,
            limit=limit,
            offset=offset
        )

        return {
            "message": "Search completed successfully" if search_results["total"] > 0 else "No results found",
            "data": search_results
        }

    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to search chats", "details": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
