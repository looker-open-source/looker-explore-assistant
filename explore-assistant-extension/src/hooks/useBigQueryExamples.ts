import { useContext, useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  setExploreGenerationExamples,
  setExploreRefinementExamples,
  setExploreSamples,
  setisBigQueryMetadataLoaded,
  setCurrenExplore,
  AssistantState,
  setBigQueryTestSuccessful
} from '../slices/assistantSlice'

import { ExtensionContext } from '@looker/extension-sdk-react'
import { useErrorBoundary } from 'react-error-boundary'
import { RootState } from '../store'

export const useBigQueryExamples = () => {

  const dispatch = useDispatch()
  const { showBoundary } = useErrorBoundary()
  const { isBigQueryMetadataLoaded } = useSelector((state: RootState) => state.assistant as AssistantState)
  
  const { core40SDK, lookerHostData } = useContext(ExtensionContext)
  const modelName = lookerHostData?.extensionId.split('::')[0]
  
  const runExampleQuery = async () => {
    try {
      const query = await core40SDK.ok(
        core40SDK.run_inline_query({
          result_format: 'json',
          body: {
            model: modelName || "explore_assistant",
            view: "explore_assistant_examples",
            fields: [`explore_assistant_examples.explore_id`, `explore_assistant_examples.examples`, `explore_assistant_refinement_examples.examples`, `explore_assistant_samples.samples`],
          }
        })
      )

      if (query === undefined) {
        return []
      }
      return query
    } catch (error) {
      if (error.name === 'LookerSDKError' || error.message === 'Model Not Found') {
        console.error('Error running query:', error.message)
        return []
      }
      showBoundary(error)
      throw new Error('error')
    }
  }

  const getExamplesAndSamples = async () => {
    return runExampleQuery().then((response) => {
      if(response.length === 0 || !Array.isArray(response)) {
        return
      }
      const generationExamples: Examples = {
        examples: {},
        refinement_examples: {},
        samples: {}
      };
      
      response.forEach((row: any) => {
        generationExamples['examples'][row['explore_assistant_examples.explore_id']] = JSON.parse(row['explore_assistant_examples.examples'])
        generationExamples['refinement_examples'][row['explore_assistant_examples.explore_id']] = JSON.parse(row['explore_assistant_refinement_examples.examples'] ?? '[]')
        generationExamples['samples'][row['explore_assistant_examples.explore_id']] = JSON.parse(row['explore_assistant_samples.samples'])
      })
      console.log('row', response[0])
      console.log('generationExamples', generationExamples)
      
      dispatch(setisBigQueryMetadataLoaded(true))
      dispatch(setExploreGenerationExamples(generationExamples['examples']))
      dispatch(setExploreRefinementExamples(generationExamples['refinement_examples']))
      dispatch(setExploreSamples(generationExamples['samples']))
      
      const exploreKey: string = response[0]['explore_assistant_examples.explore_id']
      const [modelName, exploreId] = exploreKey.split(':')
     
      dispatch(setCurrenExplore({
        exploreKey: exploreKey,
        modelName: modelName,
        exploreId: exploreId
      }))
    }).catch((error) => showBoundary(error))
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

  // Create a ref to track if the hook has already been called
  const hasFetched = useRef(false)

  // get the example prompts provide completion status
  useEffect(() => {
    if (hasFetched.current) return
    hasFetched.current = true

    // if we already fetch everything, return
    if(isBigQueryMetadataLoaded) return

    dispatch(setisBigQueryMetadataLoaded(false))
    Promise.all([getExamplesAndSamples()])
      .then(() => {
        dispatch(setisBigQueryMetadataLoaded(true))
      })
      .catch((error) => {
        showBoundary(error)
        dispatch(setisBigQueryMetadataLoaded(false))
      })
  }, [])

  return {
    testBigQuerySettings,
    getExamplesAndSamples,
  }
}