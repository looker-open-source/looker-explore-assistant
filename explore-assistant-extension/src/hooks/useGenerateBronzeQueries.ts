import { useContext, useCallback } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'

interface GenerateBronzeQueriesResponse {
  success: boolean
  message: string
  queries_generated?: number
}

const useGenerateBronzeQueries = () => {
  const { extensionSDK } = useContext(ExtensionContext)
  const { settings } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const identityToken = settings['identity_token']?.value as string || ''

  const generateBronzeQueries = useCallback(async (exploreKey: string): Promise<GenerateBronzeQueriesResponse> => {
    if (!CLOUD_RUN_URL) {
      throw new Error('Cloud Run service URL is not configured')
    }

    if (!identityToken) {
      throw new Error('Identity token is not available. Please authenticate first.')
    }

    if (!exploreKey) {
      throw new Error('Explore key is required')
    }

    // Parse the exploreKey to get model and explore names
    const [modelName, exploreName] = exploreKey.split(':')
    if (!modelName || !exploreName) {
      throw new Error('Invalid explore key format. Expected "model:explore"')
    }

    console.log('Generating bronze queries for explore:', exploreKey)
    console.log('Request URL:', CLOUD_RUN_URL)

    const payload = {
      operation: 'generate_bronze_queries',
      model_name: modelName,
      explore_name: exploreName,
      explore_key: exploreKey
    }

    try {
      const response = await extensionSDK.fetchProxy(CLOUD_RUN_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${identityToken}`,
        },
        body: JSON.stringify(payload),
      })

      // The Looker fetchProxy method returns the parsed JSON directly, not a Response object
      console.log('Bronze queries generation response:', response)
      
      // Check if the response indicates an error
      if (response && typeof response === 'object' && 'error' in response) {
        throw new Error(response.error as string || 'Unknown error from server')
      }
      
      const result = response as any
      
      return {
        success: true,
        message: result.message || `Successfully generated ${result.queries_generated || 0} bronze queries`,
        queries_generated: result.queries_generated
      }
    } catch (error) {
      console.error('Error generating bronze queries:', error)
      
      // Handle specific error cases
      const errorMessage = error instanceof Error ? error.message : String(error)
      
      if (errorMessage.includes('no recent history') || errorMessage.includes('not yet used')) {
        throw new Error('The explore is not yet used, so no queries could be retrieved.')
      }
      
      if (errorMessage.includes('Vertex AI') || errorMessage.includes('AI')) {
        throw new Error('AI service failed to generate queries. Please try again later.')
      }
      
      if (errorMessage.includes('Looker API') || errorMessage.includes('authentication')) {
        throw new Error('Looker API call failed. Please check your authentication.')
      }
      
      throw error instanceof Error ? error : new Error(String(error))
    }
  }, [CLOUD_RUN_URL, identityToken, extensionSDK])

  return {
    generateBronzeQueries
  }
}

export default useGenerateBronzeQueries
