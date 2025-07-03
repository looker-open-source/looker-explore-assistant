// Alternative implementation for calling MCP server with CORS handling
// Add this to your useSendVertexMessage.ts file

const callMCPServer = async (
  contents: string,
  parameters: ModelParameters,
) => {
  try {
    console.log('Sending request to MCP Server with content length:', contents.length);
    
    if (!oauth2Token) {
      throw new Error('OAuth token is required but not provided');
    }

    // Define default parameters
    const defaultParameters = {
      temperature: 0.2,
      maxOutputTokens: 2000,
      topP: 0.8,
      topK: 40
    };
    
    // Override default parameters with any provided
    const mergedParams = { ...defaultParameters, ...parameters };
    
    // Construct the request body for MCP server
    const requestBody = {
      contents: [{
        role: "user",
        parts: [{ text: contents }]
      }],
      generationConfig: {
        temperature: mergedParams.temperature,
        maxOutputTokens: mergedParams.maxOutputTokens,
        topP: mergedParams.topP,
        topK: mergedParams.topK
      }
    };
    
    // Call your MCP server endpoint
    const mcpEndpoint = 'https://looker-explore-assistant-mcp-730192175971.us-central1.run.app/';
    
    console.log(`Making request to MCP server: ${mcpEndpoint}`);
    
    // Use a simple approach that avoids CORS preflight by using simple CORS
    // This requires your server to handle CORS headers properly
    const response = await fetch(mcpEndpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${oauth2Token}`
      },
      body: JSON.stringify(requestBody),
      mode: 'cors',
      credentials: 'omit' // Don't send credentials to avoid preflight
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('MCP Server call failed:', errorText);
      throw new Error(`MCP Server call failed: ${response.status} - ${errorText}`);
    }
    
    const responseData = await response.json();
    console.log('MCP Server call successful, response:', responseData);
    
    return responseData;
    
  } catch (error) {
    console.error('Error calling MCP Server:', error);
    
    // Fallback to direct Vertex AI call if MCP server fails
    console.log('Falling back to direct Vertex AI call...');
    return callVertexAPI(contents, parameters);
  }
}
