import { useCallback, useContext, useRef } from 'react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'

const useSendCloudRunMessage = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings, examples, currentExplore, semanticModels, currentExploreThread, history, selectedArea, selectedExplores, availableAreas } = useSelector(
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
        
        // Build the payload for the new MCP server format
        const payload = {
          tool_name: 'generate_explore_parameters',
          arguments: {
            prompt,
            conversation_id: conversationId,
            prompt_history: promptHistory,
            thread_messages: threadToUse?.messages || [],
            current_explore: currentExplore,
            golden_queries: examples,
            semantic_models: semanticModels,
            model_name: '',
            vertex_model: vertexModel,
            test_mode: false,
            // Add area context
            selected_area: selectedArea,
            restricted_explore_keys: restrictedExploreKeys
          }
        }

        console.log('Sending payload to Cloud Run:', {
          tool_name: payload.tool_name,
          prompt: payload.arguments.prompt,
          conversation_id: payload.arguments.conversation_id,
          current_explore: payload.arguments.current_explore,
          selected_area: payload.arguments.selected_area,
          selected_explores: selectedExplores,
          restricted_explore_keys: payload.arguments.restricted_explore_keys,
          model_name: payload.arguments.model_name,
          // Don't log the entire examples and semantic_models objects as they're large
          golden_queries_keys: Object.keys(payload.arguments.golden_queries?.exploreSamples || {}),
          semantic_models_keys: Object.keys(payload.arguments.semantic_models || {}),
        })

        const result = await callCloudRunAPI(payload)
        console.log('Received result from Cloud Run:', result)
        return result
      } catch (error) {
        console.error('Error processing prompt:', error)
        throw error
      }
    },
    [currentExplore, examples, semanticModels, CLOUD_RUN_URL, identityToken, currentExploreThread, history, selectedArea, selectedExplores, availableAreas],
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
      // Simple test payload in MCP format
      const testPayload = {
        tool_name: 'generate_explore_parameters',
        arguments: {
          prompt: "test connection",
          explore_key: "test",
          model_name: "test",
          conversation_id: "test",
          vertex_model: vertexModel,
          test_mode: true
        }
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
