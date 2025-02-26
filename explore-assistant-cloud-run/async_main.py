import os
import logging
import json
from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from helper_functions import (
    validate_bearer_token,
    verify_looker_user,
    get_user_from_db,
    create_new_user,
    get_response_headers,
    DatabaseError
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
