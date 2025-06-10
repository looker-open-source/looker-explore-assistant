import { useCallback, useContext } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { AssistantState, setVertexTestSuccessful } from '../slices/assistantSlice'

const useSendCloudRunMessage = () => {
  const dispatch = useDispatch()

  const { core40SDK, lookerHostData } = useContext(ExtensionContext)

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
    if (!CLOUD_RUN_URL) {
      throw new Error('Cloud Run service URL not configured')
    }

    if (!oauth2Token) {
      throw new Error('OAuth token not available')
    }

    try {
      console.log('Calling Cloud Run service:', CLOUD_RUN_URL)
      console.log('Payload:', payload)
      
      const response = await fetch(CLOUD_RUN_URL, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${oauth2Token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(`Cloud Run API call failed: ${response.status} ${response.statusText} - ${errorText}`)
      }

      const data = await response.json()
      console.log('Cloud Run API response:', data)
      return data
    } catch (error) {
      console.error('Cloud Run API call error:', error)
      throw error
    }
  }

  // SINGLE MAIN FUNCTION - One call to process any prompt
  const processPrompt = useCallback(
    async (prompt: string, conversationId: string, promptHistory: string[] = []) => {
      try {
        // Get all available table context from current explore
        const currentSemanticModel = semanticModels[currentExploreKey]
        const dimensions = currentSemanticModel?.dimensions || []
        const measures = currentSemanticModel?.measures || []
        const tableContext = formatTableContext(dimensions, measures)
        
        // Send all available golden queries/examples
        const goldenQueries = {
          exploreEntries: examples.exploreEntries,
          exploreGenerationExamples: examples.exploreGenerationExamples,
          exploreRefinementExamples: examples.exploreRefinementExamples,
          exploreSamples: examples.exploreSamples,
        }

        const payload = {
          prompt,
          conversation_id: conversationId,
          prompt_history: promptHistory, // Send conversation history
          current_explore: currentExplore,
          golden_queries: goldenQueries,
          semantic_models: semanticModels,
          model_name: modelName,
          timestamp: new Date().toISOString(),
        }
        
        const response = await callCloudRunAPI(payload)
        
        // Expected response format:
        // {
        //   explore_params: {...},        // Looker query parameters
        //   summarized_prompt: "...",     // Cleaned up version of prompt
        //   explore_key: "...",           // Which explore to use (if different)
        //   message_type: "explore" | "summarize" | "message",
        //   summary: "...",               // If it's a summary response
        //   visualization: {...}          // Visualization parameters if applicable
        // }
        
        return response
      } catch (error) {
        console.error('Error processing prompt via Cloud Run:', error)
        throw error
      }
    },
    [formatTableContext, examples, currentExplore, semanticModels, modelName, currentExploreKey, CLOUD_RUN_URL, oauth2Token],
  )

  // Data summarization function (separate since it needs to run Looker queries first)
  const summarizeData = useCallback(
    async (exploreParams: any, conversationId: string) => {
      try {
        // Get data from Looker first
        const filters: Record<string, string> = {}
        if (exploreParams.filters !== undefined) {
          const exploreFiltters = exploreParams.filters
          Object.keys(exploreFiltters).forEach((key: string) => {
            if (!exploreFiltters[key]) {
              return
            }
            const filter: string[] | string = exploreFiltters[key]
            if (typeof filter === 'string') {
              filters[key] = filter
            }
            if (Array.isArray(filter)) {
              filters[key] = filter.join(', ')
            }
          })
        }

        const createQuery = await core40SDK.ok(
          core40SDK.create_query({
            model: currentExplore.modelName,
            view: currentExplore.exploreId,
            fields: exploreParams.fields || [],
            filters: filters,
            sorts: exploreParams.sorts || [],
            limit: exploreParams.limit || '3000',
          }),
        )

        const queryId = createQuery.id
        if (queryId === undefined || queryId === null) {
          return 'There was an error running the query!'
        }
        
        const result = await core40SDK.ok(
          core40SDK.run_query({
            query_id: queryId,
            result_format: 'md',
          }),
        )

        if (result.length === 0) {
          return 'No data returned from the query!'
        }

        // Send data to Cloud Run service for summarization
        const payload = {
          prompt: `Summarize this data`,
          conversation_id: conversationId,
          data_to_summarize: result,
          table_context: formatTableContext(semanticModels[currentExploreKey]?.dimensions || [], semanticModels[currentExploreKey]?.measures || []),
          current_explore: currentExplore,
          model_name: modelName,
          timestamp: new Date().toISOString(),
          action: 'summarize_data'
        }
        
        const response = await callCloudRunAPI(payload)
        return response.summary || 'Unable to generate summary'
      } catch (error) {
        console.error('Error summarizing data:', error)
        return 'Error generating summary'
      }
    },
    [currentExplore, semanticModels, currentExploreKey, formatTableContext, modelName, core40SDK],
  )

  const testCloudRunSettings = async () => {
    if (!CLOUD_RUN_URL) {
      console.error('Cloud Run service URL is required');
      dispatch(setVertexTestSuccessful(false));
      return false;
    }
    
    if (!oauth2Token) {
      console.error('OAuth token is required');
      dispatch(setVertexTestSuccessful(false));
      return false;
    }
    
    console.log('Testing Cloud Run service:', CLOUD_RUN_URL);
    
    try {
      const testPayload = {
        prompt: 'test connection',
        conversation_id: `test_${Date.now()}`,
        table_context: 'test context',
        current_explore: currentExplore,
        model_name: modelName,
        timestamp: new Date().toISOString(),
        test_mode: true,
      }
      
      const response = await callCloudRunAPI(testPayload)
      
      console.log('Test response received:', Boolean(response));
      
      if (response) {
        dispatch(setVertexTestSuccessful(true));
        return true;
      } else {
        console.error('Empty response from test');
        dispatch(setVertexTestSuccessful(false));
        return false;
      }
    } catch (error) {
      console.error('Error testing Cloud Run service:', error);
      dispatch(setVertexTestSuccessful(false));
      return false;
    }
  }

  const isAvailable = () => {
    return !!(CLOUD_RUN_URL && oauth2Token)
  }

  return {
    processPrompt,     // Main function for processing user prompts
    summarizeData,     // For summarizing Looker query results
    testCloudRunSettings, // For testing the service
    isAvailable,       // Check if service is configured
  }
}

export default useSendCloudRunMessage
