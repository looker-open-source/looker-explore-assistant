# MCP Server OAuth Testing Guide

This guide will help you test your MCP server deployed at:
`https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app`

## Prerequisites

1. **Google OAuth Client ID**: You need a Google OAuth Client ID configured for your domain
2. **Python 3.x** with `requests` library installed

## Method 1: Automatic OAuth Flow (Recommended)

Use the comprehensive OAuth test script:

```bash
cd /home/colin/looker-explore-assistant/explore-assistant-cloud-function
python test_mcp_with_oauth.py
```

**Before running, update the script:**
1. Edit `test_mcp_with_oauth.py`
2. Set your `GOOGLE_CLIENT_ID` at the top of the file
3. Save and run

The script will:
- ✅ Start a local callback server
- ✅ Open your browser for OAuth flow
- ✅ Use the exact same parameters as `useAutoOAuth.ts`:
  - `scope: "openid email profile"`
  - `response_type: "id_token"`
  - `nonce: <random>`
- ✅ Capture the ID token
- ✅ Test your MCP server
- ✅ Display results

## Method 2: Manual Testing (If you have a token)

If you already have a valid ID token:

```bash
python test_manual.py "YOUR_ID_TOKEN_HERE"
```

## Method 3: Browser-based Token Extraction

1. **Create OAuth URL manually:**
   - Replace `YOUR_CLIENT_ID` with your actual client ID:
   ```
   https://accounts.google.com/o/oauth2/v2/auth?client_id=YOUR_CLIENT_ID&response_type=id_token&scope=openid%20email%20profile&redirect_uri=http://localhost:8888/callback&nonce=test123
   ```

2. **Open in browser and extract token:**
   - After authentication, the browser will redirect to `localhost:8888/callback#id_token=...`
   - Copy the `id_token` value from the URL fragment

3. **Test with extracted token:**
   ```bash
   python test_manual.py "eyJhbGciOiJSUzI1NiIs..."
   ```

## Expected OAuth Parameters

Your OAuth configuration should match `useAutoOAuth.ts`:

```javascript
{
  client_id: GOOGLE_CLIENT_ID,
  scope: "openid email profile",
  response_type: "id_token", 
  nonce: <random_string>
}
```

## What the Test Does

The test will:

1. **Health Check**: Verify server is responding
2. **Token Validation**: Decode and inspect your ID token
3. **API Test**: Send a test request with proper payload structure
4. **Response Analysis**: Show server response and any errors

## Expected Test Payload

The test sends this structure (matching your frontend):

```json
{
  "prompt": "Show me total sales by region",
  "conversation_id": "test-123", 
  "prompt_history": ["Show me total sales by region"],
  "thread_messages": [],
  "current_explore": {
    "modelName": "ecommerce",
    "exploreName": "order_items" 
  },
  "golden_queries": {
    "exploreSamples": {
      "order_items": {
        "examples": []
      }
    }
  },
  "semantic_models": {},
  "model_name": "ecommerce",
  "test_mode": true
}
```

## Troubleshooting

### Common Issues:

1. **No Google Client ID**
   - Error: "GOOGLE_CLIENT_ID not set"
   - Solution: Update the script with your OAuth client ID

2. **Invalid Token Format**
   - Error: "Invalid JWT format"
   - Solution: Ensure you're using an ID token (not access token)

3. **CORS Issues**
   - The server has CORS headers configured
   - Should work from browser and command line

4. **Authentication Errors**
   - Check that your token includes `email` claim
   - Verify token hasn't expired
   - Ensure proper `aud` (audience) field

### Debug Commands:

```bash
# Test health endpoint
curl https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app/health

# Test with curl (replace TOKEN)
curl -X POST https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"prompt":"test","test_mode":true}'
```

## Server Response Examples

**Successful Response:**
```json
{
  "explore_params": {
    "model": "ecommerce",
    "explore": "order_items", 
    "measures": ["order_items.total_sale_price"],
    "dimensions": ["order_items.created_date"]
  },
  "explore_key": "order_items",
  "status": "success"
}
```

**Error Response:**
```json
{
  "error": "Authentication failed",
  "status": "error"
}
```

## Integration with Frontend

Once testing succeeds, your frontend `useSendCloudRunMessage.ts` should work with the same token from `useAutoOAuth.ts`.

The key is ensuring both use identical OAuth parameters:
- ✅ Same `client_id`
- ✅ Same `scope: "openid email profile"`  
- ✅ Same `response_type: "id_token"`
- ✅ Include `nonce` parameter
