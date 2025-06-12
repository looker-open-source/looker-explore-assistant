def format_response(status_code, message, data=None):
    response = {
        "status_code": status_code,
        "message": message,
    }
    
    if data is not None:
        response["data"] = data
    
    return response