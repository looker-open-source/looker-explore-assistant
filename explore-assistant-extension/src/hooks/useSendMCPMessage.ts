/**
 * @deprecated This hook is deprecated. Use REST API endpoints directly instead.
 * 
 * The frontend has been updated to call REST endpoints directly:
 * - System status: useSystemStatus hook with /api/v1/system-status
 * - Query processing: useSendCloudRunMessage with /api/v1/query  
 * - Olympic operations: useOlympicMigration (partially converted to REST)
 * 
 * This provides better error handling, type safety, and performance.
 */
import { useCallback, useContext } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'

interface MCPMessage {
  tool_name: string
  arguments: any
}

interface MCPResponse {
  tool: string
  status: 'success' | 'error'
  result?: any
  error?: string
}

export const useSendMCPMessage = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )

  // Cloud Run service settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const identityToken = settings['identity_token']?.value as string || ''

  const sendMCPMessage = useCallback(async (message: MCPMessage): Promise<MCPResponse> => {
    if (!CLOUD_RUN_URL) {
      throw new Error('Cloud Run URL not configured')
    }
    
    if (!identityToken) {
      throw new Error('Identity token not available')
    }

    console.log('Making MCP tool request:', { tool_name: message.tool_name, arguments: message.arguments })

    try {
      // Try fetchProxy first (preferred)
      let result: any
      try {
        console.log('Attempting fetchProxy request...')
        const proxyResponse = await extensionSDK.fetchProxy(CLOUD_RUN_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          },
          body: JSON.stringify(message),
        })
        console.log('fetchProxy request successful')
        result = proxyResponse // fetchProxy returns the parsed JSON directly
      } catch (proxyError) {
        console.warn('fetchProxy failed, falling back to direct fetch...', proxyError)
        // Fallback to direct fetch
        const response = await fetch(CLOUD_RUN_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          },
          body: JSON.stringify(message),
          mode: 'cors',
          credentials: 'omit',
        })

        if (!response.ok) {
          const errorText = await response.text()
          console.error('MCP request failed:', {
            status: response.status,
            statusText: response.statusText,
            error: errorText
          })
          throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`)
        }

        result = await response.json()
      }

      console.log('MCP tool response:', result)

      // Handle different response formats
      if (result.error) {
        throw new Error(result.error)
      }

      // Return standardized response
      return {
        tool: message.tool_name,
        status: result.status || 'success',
        result: result.result || result,
        error: result.error
      }

    } catch (error: any) {
      console.error('MCP tool call failed:', error)
      
      // Return error response in standard format
      return {
        tool: message.tool_name,
        status: 'error',
        error: error.message || 'Unknown error occurred'
      }
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  return {
    sendMCPMessage
  }
}

export default useSendMCPMessage
