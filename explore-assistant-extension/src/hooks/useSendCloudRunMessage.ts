import { useContext, useCallback } from 'react'
import { useSelector } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'

const useSendCloudRunMessage = () => {
  const { lookerHostData, extensionSDK } = useContext(ExtensionContext)

  const { settings, examples, currentExplore, semanticModels } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  // Cloud Run service settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const oauth2Token = settings['oauth2_token']?.value as string || ''

  const modelName = lookerHostData?.extensionId.split('::')[0]

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

    try {
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
        console.error('Cloud Run API error:', response.status, response.statusText)
        console.error('Response body:', response.body)
        throw new Error(`Cloud Run API error: ${response.status} ${response.statusText}`)
      }

      console.log('Cloud Run API success - response status:', response.status)
      console.log('Cloud Run API success - response body type:', typeof response.body)
      console.log('Cloud Run API success - response body:', JSON.stringify(response.body, null, 2))
      
      // Ensure we return the body directly as it should already be parsed JSON
      const result = response.body
      console.log('Returning result:', result)
      return result
    } catch (error) {
      console.error('Cloud Run API call failed:', error)
      throw error
    }
  }

  // SINGLE MAIN FUNCTION - One call to process any prompt
  const processPrompt = useCallback(
    async (prompt: string, conversationId: string, promptHistory: string[] = []) => {
      try {
        // Note: We'll need to pass thread data from the component since we can't use useSelector in callback
        // Build the payload for the Cloud Run service with conversation context
        const payload = {
          prompt,
          conversation_id: conversationId,
          prompt_history: promptHistory,
          thread_messages: [], // Will be passed by component if needed
          current_explore: currentExplore,
          golden_queries: examples,
          semantic_models: semanticModels,
          model_name: modelName,
          test_mode: false
        }

        console.log('Sending payload to Cloud Run:', payload)
        const result = await callCloudRunAPI(payload)
        console.log('Received result from Cloud Run:', result)
        console.log('Result type:', typeof result)
        console.log('Result explore_params:', result?.explore_params)
        return result
      } catch (error) {
        console.error('Error processing prompt:', error)
        throw error
      }
    },
    [currentExplore, examples, semanticModels, modelName, CLOUD_RUN_URL, oauth2Token, extensionSDK],
  )

  // Test function for Cloud Run settings
  const testCloudRunSettings = useCallback(async () => {
    try {
      if (!CLOUD_RUN_URL) {
        return false
      }

      if (!extensionSDK) {
        return false
      }

      if (!oauth2Token) {
        return false
      }
      
      // Simple test payload with test_mode flag
      const testPayload = {
        prompt: "test connection",
        explore_key: "test",
        model_name: "test",
        conversation_id: "test",
        test_mode: true  // Add test mode flag
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
        return true
      } else {
        return false
      }
    } catch (error) {
      return false
    }
  }, [CLOUD_RUN_URL, oauth2Token, extensionSDK])

  // Data summarization function
  const summarizeData = useCallback(async (exploreParams: any, conversationId: string) => {
    try {
      if (!CLOUD_RUN_URL) {
        return null
      }

      if (!oauth2Token) {
        return null
      }

      if (!extensionSDK) {
        return null
      }
      
      const payload = {
        prompt: "Please summarize this data",
        conversation_id: conversationId,
        explore_params: exploreParams,
        data_to_summarize: true, // Flag to indicate this is a summarization request
        model_name: modelName,
        current_explore: currentExplore
      }

      const response = await extensionSDK.fetchProxy(
        CLOUD_RUN_URL,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${oauth2Token}`
          },
          body: JSON.stringify(payload)
        }
      )

      if (response.ok) {
        try {
          const responseData = response.body
          return responseData.summary || responseData.message || 'Summarization completed'
        } catch (jsonError) {
          return 'Data summarization completed but response format was unexpected'
        }
      } else {
        return null
      }
    } catch (error) {
      return null
    }
  }, [CLOUD_RUN_URL, oauth2Token, extensionSDK, modelName, currentExplore])

  return {
    processPrompt,
    testCloudRunSettings,
    callCloudRunAPI,
    summarizeData
  }
}

export default useSendCloudRunMessage
