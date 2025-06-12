def context_middleware(request, handler):
    if 'context' in request:
        # Process the request with context
        return handler(request)
    else:
        # Maintain current response behavior for requests without context
        return {
            "status": "error",
            "message": "Context is required for this request."
        }