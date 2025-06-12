def auth_middleware(request):
    token = request.headers.get('Authorization')
    
    if not token or not token.startswith('Bearer '):
        return {
            'status': 'error',
            'message': 'Unauthorized: Missing or invalid token'
        }, 401
    
    # Here you would typically validate the token (e.g., check against a database or an auth service)
    # For now, we will assume the token is valid if it starts with 'Bearer '
    
    return None  # Proceed to the next middleware or handler if the token is valid