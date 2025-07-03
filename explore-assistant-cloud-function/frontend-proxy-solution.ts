// Frontend solution: Use Looker Extension Framework's built-in proxy capabilities
// This avoids CORS entirely by proxying through Looker

export const useMCPProxy = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  
  const callMCPServerViaProxy = async (requestBody: any) => {
    try {
      // Use Looker Extension SDK to make the request
      // This bypasses CORS since it's server-to-server from Looker
      const response = await extensionSDK.serverProxy(
        'https://looker-explore-assistant-mcp-730192175971.us-central1.run.app/',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${oauth2Token}`
          },
          body: JSON.stringify(requestBody)
        }
      )
      
      return response
    } catch (error) {
      console.error('Error calling MCP server via proxy:', error)
      throw error
    }
  }
  
  return { callMCPServerViaProxy }
}
