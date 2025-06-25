import { useContext, useCallback } from 'react'
import { useSelector } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'

const useSendCloudRunMessage = () => {
  const { extensionSDK } = useContext(ExtensionContext)

  const { settings, examples, currentExplore, semanticModels, currentExploreThread, history } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  // Cloud Run service settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const oauth2Token = settings['oauth2_token']?.value as string || ''

  // Use the model name from the current explore context
  // If not available, log a warning as this indicates a state issue
  const modelName = currentExplore.modelName
  if (!modelName) {
    console.warn('No model name in current explore context. This may cause issues with the Cloud Run API.')
  }

  const callCloudRunAPI = async (payload: any) => {
    if (!extensionSDK) {
      throw new Error('Extension SDK not available')
    }

    if (!CLOUD_RUN_URL) {
      throw new Error('Cloud Run service URL not configured')
    }

    if (!oauth2Token) {
      throw new Error('OAuth token not available')
    }

    // Try extension SDK proxies first (bypass CORS), then fallback to direct fetch
    const methods = [
      // Method 1: Extension fetchProxy (recommended for authenticated Cloud Run)
      async () => {
        console.log('Trying extension fetchProxy...')
        const response = await extensionSDK.fetchProxy(
          CLOUD_RUN_URL,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${oauth2Token}`,
            },
            body: JSON.stringify(payload),
          }
        )

        if (!response.ok) {
          throw new Error(`fetchProxy error: ${response.status} ${response.statusText}`)
        }

        // fetchProxy returns the parsed response body directly
        return response.body
      },
      
      // Method 2: Extension serverProxy
      async () => {
        console.log('Trying extension serverProxy...')
        const response = await extensionSDK.serverProxy(
          CLOUD_RUN_URL,
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${oauth2Token}`,
            },
            body: JSON.stringify(payload),
          }
        )

        if (!response.ok) {
          throw new Error(`serverProxy error: ${response.status} ${response.statusText}`)
        }

        // serverProxy returns the parsed response body directly
        return response.body
      },
      
      // Method 3: Direct fetch (will likely fail with authenticated Cloud Run due to CORS)
      async () => {
        console.log('Trying direct fetch as fallback (may fail due to CORS with authenticated Cloud Run)...')
        const response = await fetch(CLOUD_RUN_URL, {
          method: 'POST',
          mode: 'cors',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${oauth2Token}`,
          },
          body: JSON.stringify(payload),
        })
        
        if (!response.ok) {
          throw new Error(`Direct fetch error: ${response.status} ${response.statusText}`)
        }
        
        return await response.json()
      }
    ]

    let lastError: Error | null = null
    
    for (const method of methods) {
      try {
        console.log('Attempting API call method...')
        const result = await method()
        console.log('API call successful, result:', result)
        return result
      } catch (error) {
        console.error('Method failed with error:', error)
        if (error instanceof Error) {
          console.error('Error message:', error.message)
          console.error('Error stack:', error.stack)
        }
        lastError = error as Error
        continue
      }
    }

    throw lastError || new Error('All API call methods failed')
  }

  // SINGLE MAIN FUNCTION - One call to process any prompt
  const processPrompt = useCallback(
    async (prompt: string, conversationId: string, promptHistory: string[] = []) => {
      try {
        // Get current thread and its messages - use currentExploreThread or find from history
        const threadToUse = currentExploreThread || history?.find((t: any) => t.uuid === conversationId)
        
        // Build the payload for the Cloud Run service with conversation context
        const payload = {
          prompt,
          conversation_id: conversationId,
          prompt_history: promptHistory,
          thread_messages: threadToUse?.messages || [],
          current_explore: currentExplore,
          golden_queries: examples,
          semantic_models: semanticModels,
          model_name: modelName,
          test_mode: false
        }

        console.log('Sending payload to Cloud Run:', {
          prompt: payload.prompt,
          conversation_id: payload.conversation_id,
          current_explore: payload.current_explore,
          model_name: payload.model_name,
          // Don't log the entire examples and semantic_models objects as they're large
          golden_queries_keys: Object.keys(payload.golden_queries?.exploreSamples || {}),
          semantic_models_keys: Object.keys(payload.semantic_models || {}),
        })

        const result = await callCloudRunAPI(payload)
        console.log('Received result from Cloud Run:', result)
        return result
      } catch (error) {
        console.error('Error processing prompt:', error)
        throw error
      }
    },
    [currentExplore, examples, semanticModels, modelName, CLOUD_RUN_URL, oauth2Token, extensionSDK, currentExploreThread, history],
  )

  // Test function for Cloud Run settings
  const testCloudRunSettings = useCallback(async () => {
    try {
      if (!CLOUD_RUN_URL) {
        console.log('Cloud Run test failed: No service URL configured')
        return false
      }
      
      if (!oauth2Token) {
        console.log('Cloud Run test failed: No OAuth token available')
        return false
      }

      if (!extensionSDK) {
        console.log('Cloud Run test failed: Extension SDK not available')
        return false
      }

      console.log('Testing Cloud Run connection via extension proxy...')
      
      // Simple test payload
      const testPayload = {
        prompt: "test connection",
        explore_key: "test",
        model_name: "test",
        conversation_id: "test"
      }

      const response = await extensionSDK.fetchProxy(
        CLOUD_RUN_URL,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${oauth2Token}`
          },
          body: JSON.stringify(testPayload)
        }
      )

      if (response.ok) {
        console.log('Cloud Run test successful via extension proxy')
        return true
      } else {
        console.log('Cloud Run test failed:', response.status, response.statusText)
        return false
      }
    } catch (error) {
      console.error('Cloud Run test error:', error)
      return false
    }
  }, [CLOUD_RUN_URL, oauth2Token, extensionSDK])

  return {
    processPrompt,
    testCloudRunSettings,
    callCloudRunAPI
  }
}

export default useSendCloudRunMessage
