def parse_request(request):
    """
    Extracts and validates data from the incoming request.

    Args:
        request: The incoming request object.

    Returns:
        A dictionary containing the parsed data if valid, otherwise raises a ValueError.
    """
    # Example implementation
    if not request or not hasattr(request, 'json'):
        raise ValueError("Invalid request format")

    data = request.json()
    
    # Validate required fields
    if 'prompt' not in data:
        raise ValueError("Missing required field: 'prompt'")
    
    return data