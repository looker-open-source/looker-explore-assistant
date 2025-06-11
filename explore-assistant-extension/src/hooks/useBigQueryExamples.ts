import { useContext, useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  setExploreGenerationExamples,
  setExploreRefinementExamples,
  setExploreSamples,
  setisBigQueryMetadataLoaded,
  setCurrenExplore,
  AssistantState,
  setBigQueryTestSuccessful,
  setExploreEntries
} from '../slices/assistantSlice'

import { ExtensionContext } from '@looker/extension-sdk-react'
import { useErrorBoundary } from 'react-error-boundary'
import { RootState } from '../store'

export const useBigQueryExamples = () => {
  const dispatch = useDispatch()
  const { showBoundary } = useErrorBoundary()
  const { isBigQueryMetadataLoaded, settings } = useSelector((state: RootState) => state.assistant as AssistantState)
  
  const { core40SDK, lookerHostData } = useContext(ExtensionContext)
  const defaultModelName = lookerHostData?.extensionId.split('::')[0]
  // Use the setting if available, otherwise fallback to the default model name from extensionId
  const modelName = settings?.bigquery_example_looker_model_name?.value 
    ? String(settings.bigquery_example_looker_model_name.value)
    : defaultModelName
   
  const runExampleQuery = async () => {
    try {
      const query = await core40SDK.ok(
        core40SDK.run_inline_query({
          result_format: 'json',
          body: {
            model: modelName || "explore_assistant",
            view: "golden_queries",
            fields: [`golden_queries.explore_id`, `golden_queries.input`, `golden_queries.output`, `explore_assistant_refinement_examples.examples`, `explore_assistant_samples.samples`],
          }
        })
      )

      if (query === undefined) {
        return []
      }
      return query
    } catch (error: any) {
      if (error.name === 'LookerSDKError' || error.message === 'Model Not Found') {
        console.error('Error running query:', error.message)
        return []
      }

      // Detect OAuth-related errors and surface a user-friendly message
      if (error.message && error.message.includes('OAuth')) {
        console.error('OAuth error detected in BigQuery connection:', error.message)
        // Don't use showBoundary for OAuth errors - let the app handle gracefully
        dispatch(setBigQueryTestSuccessful(false))
        return []
      }

      console.error('Unexpected error in BigQuery query:', error)
      showBoundary(error)
      throw new Error('error')
    }
  }

  const getExamplesAndSamples = async () => {
    try {
      const response = await runExampleQuery()
      
      // Add better logging
      console.log('BQ response:', response)
      
      // Better check for empty responses
      if (!response || !Array.isArray(response) || response.length === 0) {
        console.error('Empty or invalid response from BigQuery')
        dispatch(setisBigQueryMetadataLoaded(false))
        dispatch(setBigQueryTestSuccessful(false))
        return
      }
      
      // Store the raw response for later filtering
      dispatch(setExploreEntries(response))
      
      // We'll still process the data as before to maintain backward compatibility
      const generationExamples: {
        examples: Record<string, any[]>;
        refinement_examples: Record<string, any>;
        samples: Record<string, any>;
      } = {
        examples: {},
        refinement_examples: {},
        samples: {}
      };
      
      // Group examples by explore_id
      const exploreExamples: Record<string, any[]> = {};
      
      // First pass: group all examples by explore ID and collect refinement examples and samples
      response.forEach((row: any) => {
        try {
          const exploreId = row['golden_queries.explore_id'];
          console.log(`Processing row for explore: ${exploreId}`);
          
          if (!exploreId) {
            console.error('Missing explore_id in response row', row);
            return;
          }
          
          // Initialize the examples structure for this explore_id if it doesn't exist
          if (!exploreExamples[exploreId]) {
            exploreExamples[exploreId] = [];
          }
          
          // Add the individual input/output example
          const input = row['golden_queries.input'];
          const output = row['golden_queries.output'];
          
          if (input && output) {
            exploreExamples[exploreId].push({
              input: input,
              output: output
            });
          }
          
          // Only process refinement examples and samples once per explore_id
          if (!generationExamples.refinement_examples[exploreId]) {
            generationExamples.refinement_examples[exploreId] = 
              safeJsonParse(row['explore_assistant_refinement_examples.examples'], [], 'refinement_examples');
          }
          
          if (!generationExamples.samples[exploreId]) {
            generationExamples.samples[exploreId] = 
              safeJsonParse(row['explore_assistant_samples.samples'], [], 'samples');
          }
        } catch (err) {
          console.error('Error processing row:', err, row);
        }
      });
      
      // Assign processed examples to the final structure
      generationExamples.examples = exploreExamples;
      
      console.log('Processed generationExamples:', generationExamples);
      
      // Check if we have any examples
      const hasExamples = Object.keys(generationExamples.examples).length > 0
      const hasSamples = Object.keys(generationExamples.samples).length > 0
      
      if (!hasExamples || !hasSamples) {
        console.warn('Missing examples or samples data', {hasExamples, hasSamples})
      }
      
      // Set the data in Redux
      dispatch(setExploreGenerationExamples(generationExamples.examples))
      dispatch(setExploreRefinementExamples(generationExamples.refinement_examples))
      dispatch(setExploreSamples(generationExamples.samples))
      
      // Set the current explore
      if (response[0] && response[0]['golden_queries.explore_id']) {
        const exploreKey = response[0]['golden_queries.explore_id']
        const [modelName, exploreId] = String(exploreKey).split(':')
        
        dispatch(setCurrenExplore({
          exploreKey,
          modelName,
          exploreId
        }))
      }
      
      // Mark as loaded even if we have issues
      dispatch(setisBigQueryMetadataLoaded(true))
      dispatch(setBigQueryTestSuccessful(true))
      
    } catch (error) {
      console.error('Error in getExamplesAndSamples:', error)
      dispatch(setisBigQueryMetadataLoaded(false))
      dispatch(setBigQueryTestSuccessful(false))
      showBoundary(error)
    }
  }

  // Helper function for safe JSON parsing
  function safeJsonParse(jsonString: string | null | undefined, defaultValue: any, fieldName: string) {
    if (!jsonString) {
      console.warn(`Empty ${fieldName} value`)
      return defaultValue
    }
    
    try {
      return JSON.parse(jsonString)
    } catch (err) {
      console.error(`Error parsing ${fieldName} JSON:`, err)
      console.log('Raw string:', jsonString)
      return defaultValue
    }
  }

  const testBigQuerySettings = async () => {

    console.log('testBigQuerySettings')
    try {
      const response = await runExampleQuery()
      if (response.length > 0) {
        dispatch(setBigQueryTestSuccessful(true))
      } else {
        dispatch(setBigQueryTestSuccessful(false))
      }
      return response.length > 0
    } catch (error) {
      dispatch(setBigQueryTestSuccessful(false))
      console.error('Error testing BigQuery settings:', error)
      return false
    }
  }

  // Create refs to track state between renders
  const hasFetched = useRef(false)
  const lastModelName = useRef<string | null>(null)

  // get the example prompts provide completion status
  useEffect(() => {
    // Check if model name changed since last fetch
    const modelNameChanged = lastModelName.current !== null && 
                             lastModelName.current !== modelName;
    
    if (modelNameChanged) {
      console.log(`Model name changed from ${lastModelName.current} to ${modelName}, forcing re-fetch`);
      hasFetched.current = false;
      dispatch(setisBigQueryMetadataLoaded(false));
    }

    // Update last model name reference
    lastModelName.current = modelName || null;
    
    // Debounce to prevent multiple rapid state changes
    let activeRequest = true
    
    // Skip if we've already fetched AND the data is loaded
    if (hasFetched.current || isBigQueryMetadataLoaded) {
      console.log('Already fetching or metadata loaded, skipping')
      return
    }
    hasFetched.current = true
    
    // Set loading state only once at beginning of request
    if (!isBigQueryMetadataLoaded) {
      dispatch(setisBigQueryMetadataLoaded(false))
    }
    
    // Add timeout in case fetch hangs
    const timeoutId = setTimeout(() => {
      console.warn('BigQuery fetch timeout exceeded, forcing initialization')
      if (activeRequest) {
        console.log('TIMEOUT: Setting isBigQueryMetadataLoaded to true')
        dispatch(setisBigQueryMetadataLoaded(true))
      }
    }, 10000) // 10 second timeout

    getExamplesAndSamples()
      .then(() => {
        if (activeRequest) {
          clearTimeout(timeoutId)
          console.log('SUCCESS: Setting isBigQueryMetadataLoaded to true')
          dispatch(setisBigQueryMetadataLoaded(true))
          dispatch(setBigQueryTestSuccessful(true))
        }
      })
      .catch((error) => {
        if (activeRequest) {
          clearTimeout(timeoutId)
          console.error('Failed to fetch examples and samples:', error)
          console.log('ERROR: Setting isBigQueryMetadataLoaded to false')
          dispatch(setisBigQueryMetadataLoaded(false))
          dispatch(setBigQueryTestSuccessful(false))
          // Reset hasFetched to allow retry on next render
          hasFetched.current = false
        }
      })
      
    // Cleanup function to prevent setState after unmount
    return () => {
      activeRequest = false
      clearTimeout(timeoutId)
    }

  }, [
    settings?.bigquery_example_looker_model_name?.value, 
    modelName,
    dispatch, 
    isBigQueryMetadataLoaded,
    getExamplesAndSamples
  ])

  return {
    testBigQuerySettings,
    getExamplesAndSamples,
  }
}