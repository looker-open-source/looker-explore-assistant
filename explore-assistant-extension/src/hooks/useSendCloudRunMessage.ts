import { useCallback, useContext, useRef } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'

const useSendCloudRunMessage = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings, examples, semanticModels, currentExploreThread, history, selectedArea, selectedExplores, availableAreas } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  // Cloud Run service settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const identityToken = settings['identity_token']?.value as string || ''
  const vertexModel = settings['vertex_model']?.value as string || 'gemini-2.0-flash'

  const callCloudRunAPI = async (payload: any) => {
    if (!CLOUD_RUN_URL) {
      throw new Error('Cloud Run service URL not configured')
    }

    if (!identityToken) {
      throw new Error('Identity token not available')
    }

    console.log('Making request to Cloud Run service using Identity token...')
    console.log('Request URL:', CLOUD_RUN_URL)
    
    try {
      // Try fetchProxy first (preferred)
      try {
        console.log('Attempting fetchProxy request with Bearer token...')
        const response = await extensionSDK.fetchProxy(CLOUD_RUN_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          },
          body: JSON.stringify(payload),
        })
        console.log('fetchProxy request successful')
        return response
      } catch (proxyError) {
        console.warn('fetchProxy failed, falling back to direct fetch...', proxyError)
        // Fallback to direct fetch
        const response = await fetch(CLOUD_RUN_URL, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${identityToken}`,
          },
          body: JSON.stringify(payload),
          mode: 'cors',
          credentials: 'omit',
        })
        if (response.ok) {
          console.log('Direct fetch with Bearer token successful')
          return await response.json()
        } else {
          const errorText = await response.text()
          throw new Error(`Cloud Run fetch error: ${response.status} ${response.statusText} - ${errorText}`)
        }
      }
    } catch (error) {
      console.error('Cloud Run request failed:', error)
      throw new Error(`Unable to connect to Cloud Run service: ${error}`)
    }
  }

  const processPrompt = useCallback(
    async (prompt: string, conversationId: string, promptHistory: string[] = []) => {
      try {
        // Get current thread and its messages - use currentExploreThread or find from history
        const threadToUse = currentExploreThread || history?.find((t: any) => t.uuid === conversationId)
        
        // Get explore keys for selected area if area is selected
        const selectedAreaData = selectedArea ? availableAreas.find(area => area.area === selectedArea) : null
        
        // Use selected explores if any are chosen, otherwise use all explores from the area
        let restrictedExploreKeys: string[] = []
        if (selectedExplores && selectedExplores.length > 0) {
          // User has specifically selected explores
          restrictedExploreKeys = selectedExplores
        } else if (selectedAreaData) {
          // User selected an area but no specific explores, use all from the area
          restrictedExploreKeys = selectedAreaData.explore_keys
        }
        // If no area or explores selected, restrictedExploreKeys remains empty (no restrictions)
        
        // Build the payload for the Cloud Run service with conversation context
        // Note: current_explore and model_name are ignored by backend in favor of AI selection
        const payload = {
          prompt,
          conversation_id: conversationId,
          prompt_history: promptHistory,
          thread_messages: threadToUse?.messages || [],
          golden_queries: examples,
          semantic_models: semanticModels,
          vertex_model: vertexModel,
          test_mode: false,
          // Area context for explore restriction
          restricted_explore_keys: restrictedExploreKeys
        }

        console.log('Sending payload to Cloud Run:', {
          prompt: payload.prompt,
          conversation_id: payload.conversation_id,
          vertex_model: payload.vertex_model,
          selected_explores: selectedExplores,
          restricted_explore_keys: payload.restricted_explore_keys,
          // Log structure info without full content to avoid console clutter
          golden_queries_structure: {
            exploreEntries: Array.isArray(payload.golden_queries?.exploreEntries) ? payload.golden_queries.exploreEntries.length : 'not_array',
            exploreGenerationExamples: typeof payload.golden_queries?.exploreGenerationExamples === 'object' ? Object.keys(payload.golden_queries.exploreGenerationExamples).length : 'not_object',
            exploreRefinementExamples: typeof payload.golden_queries?.exploreRefinementExamples === 'object' ? Object.keys(payload.golden_queries.exploreRefinementExamples).length : 'not_object',
            exploreSamples: typeof payload.golden_queries?.exploreSamples === 'object' ? Object.keys(payload.golden_queries.exploreSamples).length : 'not_object'
          },
          semantic_models_count: typeof payload.semantic_models === 'object' ? Object.keys(payload.semantic_models || {}).length : 'not_object',
        })

        const result = await callCloudRunAPI(payload)
        console.log('Received result from Cloud Run:', result)
        return result.body
      } catch (error) {
        console.error('Error processing prompt:', error)
        throw error
      }
    },
    [examples, semanticModels, CLOUD_RUN_URL, identityToken, currentExploreThread, history, selectedExplores, availableAreas],
  )

  // Test function for Cloud Run settings
  const testInFlight = useRef(false)

  const testCloudRunSettings = useCallback(async () => {
    console.log('Starting Cloud Run settings test...')
    if (testInFlight.current) {
      // If a test is already running, do not start another; return false (no-op)
      return false
    }
    testInFlight.current = true
    try {
      if (!CLOUD_RUN_URL) {
        console.log('Cloud Run test failed: No service URL configured')
        testInFlight.current = false
        return false
      }
      if (!identityToken) {
        console.log('Cloud Run test failed: No Identity token available')
        testInFlight.current = false
        return false
      }
      console.log('Testing Cloud Run connection using Identity token...')
      // Simple test payload
      const testPayload = {
        prompt: "test connection",
        explore_key: "test",
        model_name: "test",
        conversation_id: "test",
        vertex_model: vertexModel,
        test_mode: true
      }
      try {
        // Try fetchProxy first
        await extensionSDK.fetchProxy(CLOUD_RUN_URL, {
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
      testInFlight.current = false
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  return {
    processPrompt,
    testCloudRunSettings,
    callCloudRunAPI
  }
}

export default useSendCloudRunMessage
