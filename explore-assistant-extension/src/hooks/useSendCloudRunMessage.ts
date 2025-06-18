import { useContext, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { AssistantState } from '../slices/assistantSlice'

const useSendCloudRunMessage = () => {
  const dispatch = useDispatch()

  const { core40SDK, lookerHostData, extensionSDK } = useContext(ExtensionContext)

  const { settings, examples, currentExplore, semanticModels } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  // Cloud Run service settings
  const CLOUD_RUN_URL = settings['cloud_run_service_url']?.value as string || ''
  const oauth2Token = settings['oauth2_token']?.value as string || ''

  const currentExploreKey = currentExplore.exploreKey
  const modelName = lookerHostData?.extensionId.split('::')[0]

  // Helper function to format table context
  const formatTableContext = useCallback((dimensions: any[], measures: any[]) => {
    const formatRow = (field: {
      name?: string
      type?: string
      label?: string
      description?: string
      tags?: string[]
    }) => {
      const name = field.name || ''
      const type = field.type || ''
      const label = field.label || ''
      const description = field.description || ''
      const tags = field.tags ? field.tags.join(', ') : ''
      return `| ${name} | ${type} | ${label} | ${description} | ${tags} |`
    }

    return `
# Looker Explore Metadata
Model: ${currentExplore.modelName}
Explore: ${currentExplore.exploreId}

## Dimensions (for grouping data):
| Field Id | Field Type | Label | Description | Tags |
|----------|------------|-------|-------------|------|
${dimensions.map(formatRow).join('\n')}

## Measures (for calculations):
| Field Id | Field Type | Label | Description | Tags |
|----------|------------|-------|-------------|------|
${measures.map(formatRow).join('\n')}
`
  }, [currentExplore])

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
        throw new Error(`Cloud Run API error: ${response.status} ${response.statusText}`)
      }

      return await response.json()
    } catch (error) {
      console.error('Cloud Run API call failed:', error)
      throw error
    }
  }

  // SINGLE MAIN FUNCTION - One call to process any prompt
  const processPrompt = useCallback(
    async (prompt: string, conversationId: string, promptHistory: string[] = []) => {
      try {
        // Build the payload for the Cloud Run service
        const payload = {
          prompt,
          conversation_id: conversationId,
          prompt_history: promptHistory,
          explore_key: currentExploreKey,
          model_name: modelName,
          // Add other necessary data...
        }

        const result = await callCloudRunAPI(payload)
        return result
      } catch (error) {
        console.error('Error processing prompt:', error)
        throw error
      }
    },
    [formatTableContext, examples, currentExplore, semanticModels, modelName, currentExploreKey, CLOUD_RUN_URL, oauth2Token, extensionSDK],
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
