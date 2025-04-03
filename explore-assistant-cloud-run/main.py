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
    LoginRequest, ThreadRequest, MessageRequest, FeedbackRequest,
    BaseResponse, ThreadHistoryResponse, SearchResponse
)
from database import get_session
from helper_functions import (
    validate_bearer_token,
    verify_looker_user,
    get_user_from_db,
    create_new_user,
    create_chat_thread,
    retrieve_thread_history,
    add_message,
    add_feedback,
    generate_response,
    generate_looker_query,
    DatabaseError,
    update_message_db,
    search_thread_history
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
            "message": contents,
            "parameters": json.dumps(parameters),
            "response": response_text,
            "recorded_at": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M:%S.%f")
        }]
        
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

@app.post("/thread")
async def create_thread(
    request: ThreadRequest,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
):
    try:
        thread_id = create_chat_thread(request.user_id, request.explore_key)
        if not thread_id:
            raise HTTPException(status_code=500, detail="Failed to create chat thread")
            
        return BaseResponse(
            message="Thread created successfully",
            data={"thread_id": thread_id, "status": "created"}
        )
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})

@app.get("/thread/history")
async def thread_history(
    user_id: str,
    thread_id: str,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
):
    try:
        thread_history_data = retrieve_thread_history(thread_id)
        
        # Case 1: First-time user with no thread history
        if not thread_history_data:
            return ThreadHistoryResponse(
                message="No thread history found for user",
                data={"threads": []}
            )
            
        # Case 2: Normal case with existing history
        return ThreadHistoryResponse(**thread_history_data)
        
    except DatabaseError as e:
        # Case 3: Database or server-related errors
        raise HTTPException(
            status_code=503, 
            detail={
                "error": "Service temporarily unavailable",
                "message": "Failed to retrieve thread history",
                "details": e.args[0]
            }
        )
    except Exception as e:
        # Case 4: Other unexpected errors
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "details": str(e)
            }
        )

@app.post("/message")
async def handle_message(
    request: MessageRequest,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
):
    try:
        thread_id = request.current_thread_id

        if not thread_id:
            raise HTTPException(status_code=500, detail="Failed to create message thread")

        if not request.message_id:
            # scenario : FE send request to generate a message ID
            # the endpoint will return a message id of the logged data
            # WITHOUT any LLM processing; FE will the resend the message with new id
            # to continue the process.
            new_id = add_message(
                message_id=None,
                thread_id=request.current_thread_id,
                contents=request.contents,
                prompt_type=request.prompt_type,
                current_explore_key=request.current_explore_key,
                raw_prompt=request.raw_prompt,
                user_id=request.user_id,
                is_user=request.is_user
            )
            
            return BaseResponse(
                message="Message ID generated successfully",
                data={"message_id": new_id}
            )

        elif request.message_id:
            # scenario : FE sends the message with valid message id to LLM.
            # the endpoint will now pass the message to LLM and return the results
            response_text = generate_response(
                request.contents,
                request.parameters
                )
            
            # update the logged message record with LLM response
            updated_message = update_message_db(
                message_id=request.message_id,
                thread_id=request.current_thread_id,
                contents=request.contents,
                prompt_type=request.prompt_type,
                current_explore_key=request.current_explore_key,
                raw_prompt=request.raw_prompt,
                user_id=request.user_id,
                is_user=request.is_user,
                llm_response=response_text
            )

            logger.info(f"LLM Response: {response_text}")
            
            return BaseResponse(
                message="Message handled successfully",
                data={"response": response_text, "thread_id": thread_id}
            )
        
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/message/update")
async def update_message(
    update_fields: dict,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
):
    try:

        updated_message = update_message_db(**update_fields)
        
        return BaseResponse(
            message="Message updated successfully",
            data={"response": updated_message}
            )
    
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
            return BaseResponse(
                message="Feedback submitted successfully",
                data={"response": result}
                )
        else:
            raise HTTPException(status_code=500, detail="Failed to submit feedback")
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail={"error": e.args[0], "details": e.details})

@app.get("/thread/search")
async def search_threads(
    user_id: str,
    search_query: str,
    limit: int = 10,
    offset: int = 0,
    authorized: bool = Depends(validate_token),
    db: Session = Depends(get_session)
) -> SearchResponse:
    try:
        search_results = search_thread_history(
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
            detail={"error": "Failed to search thread history", "details": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info", reload=True)
