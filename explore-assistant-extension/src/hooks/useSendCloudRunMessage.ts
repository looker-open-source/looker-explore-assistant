import { useCallback, useContext, useRef } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'

const useSendCloudRunMessage = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings, examples, currentExplore, semanticModels, currentExploreThread, history } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  // Cloud Run service settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const identityToken = settings['identity_token']?.value as string || ''

  // Use the model name from the current explore context
  // If not available, log a warning as this indicates a state issue
  const modelName = currentExplore.modelName
  if (!modelName) {
    console.warn('No model name in current explore context. This may cause issues with the Cloud Run API.')
  }

  const callCloudRunAPI = async (payload: any) => {
    if (!CLOUD_RUN_URL) {
      throw new Error('Cloud Run service URL not configured')
    }

    if (!identityToken) {
      throw new Error('Identity token not available')
    }

    console.log('Making request to Cloud Run service using Identity token...')
    console.log('Request URL:', CLOUD_RUN_URL)
    console.log('Payload keys:', Object.keys(payload))
    
    try {
      // First, let's try a simple request that won't trigger CORS preflight
      // Use text/plain content type to avoid preflight for testing
      console.log('Attempting simple CORS request without preflight...')
      
      const simpleResponse = await fetch(CLOUD_RUN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'text/plain', // This avoids CORS preflight
        },
        body: JSON.stringify(payload),
        mode: 'cors',
      })
      
      if (simpleResponse.ok) {
        console.log('Simple CORS request successful (no auth needed)')
        return await simpleResponse.json()
      } else {
        console.log('Simple CORS failed, trying with auth...')
      }
      
      // If simple request fails, try fetchProxy with identity token
      console.log('Trying fetchProxy with authentication...')
      const response = await extensionSDK.fetchProxy(CLOUD_RUN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify(payload),
      })
      
      console.log('Cloud Run API response received via fetchProxy:', typeof response)
      return response
    } catch (error) {
      console.error('All requests failed:', error)
      console.error('Error details:', JSON.stringify(error, null, 2))
      
      // Last resort: try with proper auth headers
      console.log('Final attempt: direct fetch with proper CORS and auth...')
      try {
        const response = await fetch(CLOUD_RUN_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          },
          body: JSON.stringify(payload),
          mode: 'cors',
          credentials: 'omit', // Don't send cookies to avoid additional preflight
        })
        
        if (!response.ok) {
          const errorText = await response.text()
          throw new Error(`Final fetch error: ${response.status} ${response.statusText} - ${errorText}`)
        }
        
        console.log('Final direct fetch successful')
        return await response.json()
      } catch (finalError) {
        console.error('All connection attempts failed:', finalError)
        
        throw new Error(`Unable to connect to Cloud Run service:
          Error: ${finalError}
          
          Troubleshooting steps:
          1. Check that your Cloud Run URL is correct: ${CLOUD_RUN_URL}
          2. Verify your OAuth token is valid
          3. Ensure Cloud Run service is accepting requests
          4. Check Cloud Run logs for authentication errors`)
      }
    }
  }

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
    [currentExplore, examples, semanticModels, modelName, CLOUD_RUN_URL, identityToken, currentExploreThread, history],
  )

  // Test function for Cloud Run settings
  const testInFlight = useRef<Promise<boolean> | null>(null)

  const testCloudRunSettings = useCallback(async () => {
    if (testInFlight.current) {
      // If a test is already running, return the same promise
      return testInFlight.current
    }
    const testPromise = (async () => {
      try {
        if (!CLOUD_RUN_URL) {
          console.log('Cloud Run test failed: No service URL configured')
          return false
        }
        if (!identityToken) {
          console.log('Cloud Run test failed: No Identity token available')
          return false
        }
        console.log('Testing Cloud Run connection using Identity token...')
        // Simple test payload
        const testPayload = {
          prompt: "test connection",
          explore_key: "test",
          model_name: "test",
          conversation_id: "test",
          test_mode: true
        }
        try {
          // Try fetchProxy first
          const result = await extensionSDK.fetchProxy(CLOUD_RUN_URL, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${identityToken}`
            },
            body: JSON.stringify(testPayload)
          })
          console.log('Cloud Run test successful via fetchProxy')
          return true
        } catch (fetchProxyError) {
          console.log('fetchProxy failed, trying direct fetch...', fetchProxyError)
          // Fallback to direct fetch
          const response = await fetch(CLOUD_RUN_URL, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${identityToken}`
            },
            body: JSON.stringify(testPayload)
          })
          if (response.ok) {
            console.log('Cloud Run test successful via direct fetch')
            return true
          } else {
            console.log('Cloud Run test failed:', response.status, response.statusText)
            return false
          }
        }
      } catch (error) {
        console.error('Cloud Run test error:', error)
        return false
      } finally {
        testInFlight.current = null
      }
    })()
    testInFlight.current = testPromise
    return testPromise
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  return {
    processPrompt,
    testCloudRunSettings,
    callCloudRunAPI
  }
}

export default useSendCloudRunMessage
