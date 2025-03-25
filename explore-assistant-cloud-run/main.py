import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Union
from fastapi import FastAPI, Request, HTTPException, Response, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import json
from sqlmodel import Session
from models import (
    LoginRequest, ChatRequest, PromptRequest, FeedbackRequest,
    BaseResponse, ErrorResponse, ChatHistoryResponse, SearchResponse
)
from database import get_session
from helper_functions import (
    validate_bearer_token,
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# OAuth validation dependency
async def validate_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    if not validate_bearer_token(credentials.credentials):
        raise HTTPException(
            status_code=403,
            detail="Invalid token"
        )
    return True

app = FastAPI()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": str(exc)
        }
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/")
async def base(
    request: Request,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
):
    incoming_request = await request.json()
    contents = incoming_request.get("contents")
    parameters = incoming_request.get("parameters")

    try:
        response_text = generate_looker_query(contents, parameters)
        logger.info(f"endpoint root - LLM response : {response_text}")

        data = [{
            "prompt": contents,
            "parameters": json.dumps(parameters),
            "response": response_text,
            "recorded_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S.%f")
        }]
        record_prompt(data)
        
        return BaseResponse(message="Query generated successfully", data={"response": response_text})
    except TimeoutError:
        raise HTTPException(status_code=504, detail="Request timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
async def login(
    request: LoginRequest,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
):
    if not verify_looker_user(request.user_id):
        raise HTTPException(status_code=403, detail="User is not a validated Looker user")
    
    try: 
        user_data = get_user_from_db(request.user_id)
        if user_data:
            return BaseResponse(message="User already exists", data=user_data)

        result = create_new_user(request.user_id, request.name, request.email)
        return BaseResponse(message="User created successfully", data=result)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})

@app.post("/chat")
async def create_chat(
    request: ChatRequest,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
):
    try:
        chat_id = create_chat_thread(request.user_id, request.explore_key)
        if not chat_id:
            raise HTTPException(status_code=500, detail="Failed to create chat thread")
            
        return BaseResponse(
            message="Chat created successfully",
            data={"chat_id": chat_id, "status": "created"}
        )
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})

@app.get("/chat/history")
async def chat_history(
    user_id: str,
    chat_id: str,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
):
    try:
        chat_history_data = retrieve_chat_history(chat_id)
        if not chat_history_data or not chat_history_data.get("data"):
            raise HTTPException(status_code=404, detail="Chat history not found")
        return ChatHistoryResponse(**chat_history_data)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})

@app.post("/prompt")
async def handle_prompt(
    request: PromptRequest,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
):
    try:

        response_text = generate_response(request.contents, 
                                              request.parameters)
        logger.info(f"LLM Response: {response_text}")
            
        chat_id = request.current_thread_id

        if not chat_id:
            raise HTTPException(status_code=500, detail="Failed to create chat thread")

        user_message_id = add_message(chat_id, 
                                      request.user_id,
                                      request.contents or request.raw_prompt,
                                      True)
        if not user_message_id:
            raise HTTPException(status_code=500, detail="Failed to add user message")

        # bot_message_id = add_message(chat_id,
        #                              request.user_id,
        #                              response_text,False)
        # if not bot_message_id:
        #     raise HTTPException(status_code=500, detail="Failed to add bot message")

        return BaseResponse(
            message="Prompt handled successfully",
            data={"response": response_text, "chat_id": chat_id}
        )
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
async def give_feedback(
    request: FeedbackRequest,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
):
    try:
        result = add_feedback(request.user_id, request.message_id, request.feedback_text, request.is_positive)
        if result:
            return {"message": "Feedback submitted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to submit feedback")
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})

@app.get("/chat/search")
async def search_chats(
    user_id: str,
    search_query: str,
    limit: int = 10,
    offset: int = 0,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
) -> SearchResponse:
    try:
        search_results = search_chat_history(
            user_id=user_id,
            search_query=search_query,
            limit=limit,
            offset=offset
        )

        message = "Search completed successfully" if search_results["total"] > 0 else "No results found"
        return SearchResponse(
            message=message,
            data=search_results
        )

    except DatabaseError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "Failed to search chats", "details": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info", reload=True)
