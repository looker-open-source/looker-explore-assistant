import { useContext, useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  setExploreGenerationExamples,
  setExploreRefinementExamples,
  setExploreSamples,
  ExploreSamples,
  setisBigQueryMetadataLoaded,
  setCurrenExplore,
  RefinementExamples,
  ExploreExamples,
  AssistantState,
  Examples
} from '../slices/assistantSlice'

import { ExtensionContext } from '@looker/extension-sdk-react'
import process from 'process'
import { useErrorBoundary } from 'react-error-boundary'
import { RootState } from '../store'

export const useBigQueryExamples = () => {
  const connectionName = process.env.BIGQUERY_EXAMPLE_PROMPTS_CONNECTION_NAME || ''
  const datasetName = process.env.BIGQUERY_EXAMPLE_PROMPTS_DATASET_NAME || 'explore_assistant'
  const examplesModelName = process.env.BIGQUERY_EXAMPLES_LOOKER_MODEL_NAME || 'explore_assistant'

  const dispatch = useDispatch()
  const { showBoundary } = useErrorBoundary()
  const { isBigQueryMetadataLoaded } = useSelector((state: RootState) => state.assistant as AssistantState)

  const { core40SDK } = useContext(ExtensionContext)

  const runExampleQuery = async () => {

    try {
      const query = await core40SDK.ok(
        core40SDK.run_inline_query({
          result_format: 'json',
          body: {
            model:examplesModelName,
            view: "explore_assistant_examples",
            fields: [`explore_assistant_examples.explore_id`,`explore_assistant_examples.examples`,`explore_assistant_refinement_examples.examples`,`explore_assistant_samples.samples`],
          }
        })
      )
        
      if (query === undefined) {
        return []
      }
      return query
    } catch(error) {
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
      
      if(response.length === 0 || !Array.isArray(response)) {
        return
      }
      response.forEach((row: any) => {
        generationExamples['examples'][row['explore_assistant_examples.explore_id']] = JSON.parse(row['explore_assistant_examples.examples'])
        generationExamples['refinement_examples'][row['explore_assistant_examples.explore_id']] = JSON.parse(row['explore_assistant_refinement_examples.examples'] ?? '[]')
        generationExamples['samples'][row['explore_assistant_examples.explore_id']] = JSON.parse(row['explore_assistant_samples.samples'])
      })
      
      dispatch(setExploreGenerationExamples(generationExamples['examples']))
      dispatch(setExploreRefinementExamples(generationExamples['refinement_examples']))
      const exploreKey: string = response[0]['explore_assistant_examples.explore_id']
      
      const [modelName, exploreId] = exploreKey.split(':')
     
      dispatch(setExploreSamples(generationExamples['samples']))
      dispatch(setCurrenExplore({
        exploreKey: exploreKey,
        modelName: modelName,
        exploreId: exploreId
      }))
    }).catch((error) => showBoundary(error))
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
  }, [showBoundary])
}
