import { useContext, useEffect } from 'react'
import { useDispatch } from 'react-redux'
import {
  setExploreExamplesById,
  setExploreGenerationExamples,
  setExploreRefinementExamples,
  setExploreSamplesById,
} from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'
import process from 'process'
import { useErrorBoundary } from 'react-error-boundary'

export const useBigQueryExamples = () => {
  const connectionName =
    process.env.BIGQUERY_EXAMPLE_PROMPTS_CONNECTION_NAME || ''
  const LOOKER_MODEL = process.env.LOOKER_MODEL || ''
  const LOOKER_EXPLORE = process.env.LOOKER_EXPLORE || ''
  const datasetName =
    process.env.BIGQUERY_EXAMPLE_PROMPTS_DATASET_NAME || 'explore_assistant'

  const dispatch = useDispatch()
  const { showBoundary } = useErrorBoundary()

  const { core40SDK } = useContext(ExtensionContext)

  const runExampleQuery = async (sql: string) => {
    try {
      const createSqlQuery = await core40SDK.ok(
        core40SDK.create_sql_query({
          connection_name: connectionName,
          sql: sql,
        }),
      )
      const { slug } = await createSqlQuery
      if (slug) {
        const runSQLQuery = await core40SDK.ok(
          core40SDK.run_sql_query(slug, 'json'),
        )
        const examples = await runSQLQuery
        return examples
      }
      return []
    } catch (error) {
      showBoundary(error)
      throw new Error('error')
    }
  }

  // Function to transform the response
  const transformResponse = (response: any[]) => {
    const examplesById: {
      [exploreId: string]: { input: string; output: string }[]
    } = {}
    const samplesById: {
      [exploreId: string]: {
        category: string
        prompt: string
        color: string
      }[]
    } = {}

    response.forEach((item) => {
      // Parse the examples if it's a string
      const examples =
        typeof item.examples === 'string'
          ? JSON.parse(item.examples)
          : item.examples
      const samples =
        typeof item.samples === 'string'
          ? JSON.parse(item.samples)
          : item.samples

      // Transform the explore_id from str1:str2 to str1/str2
      const transformedExploreId = item.explore_id.replace(':', '/')

      examplesById[transformedExploreId] = examples
      samplesById[transformedExploreId] = samples
    })

    return { examplesById, samplesById }
  }
  const getExamplePrompts = async () => {
    const sql = `
      SELECT
          examples.explore_id,
          examples.examples,
          samples.samples
      FROM
        \`${datasetName}.explore_assistant_examples\` AS examples
      LEFT JOIN
        \`${datasetName}.explore_assistant_samples\` AS samples
      ON
        examples.explore_id = samples.explore_id
    `

    return runExampleQuery(sql)
      .then((response) => {
        let parsedResponse: any[] = []
        // Parse the response if it's a string
        if (typeof response === 'string') {
          try {
            parsedResponse = JSON.parse(response)
          } catch (error) {
            console.error('Error parsing response:', error)
          }
        } else if (Array.isArray(response)) {
          parsedResponse = response
        } else {
          console.error('Unexpected response type:', typeof response)
        }

        // Ensure the response is an array before processing
        if (!Array.isArray(parsedResponse)) {
          console.error('Response is not an array')
          return
        }

        // Transform the response
        const { examplesById, samplesById } = transformResponse(parsedResponse)

        // const generationExamples = JSON.parse(parsedResponse[0]['examples'])
        const generationExamples =
          examplesById[`${LOOKER_MODEL}/${LOOKER_EXPLORE}`]

        // Dispatch the action
        dispatch(setExploreExamplesById(examplesById))
        dispatch(setExploreSamplesById(samplesById))
        dispatch(setExploreGenerationExamples(generationExamples))
      })
      .catch((error) => showBoundary(error))
  }

  const getRefinementPrompts = async () => {
    const sql = `
    SELECT
        examples
    FROM
      \`${datasetName}.explore_assistant_refinement_examples\`
      WHERE explore_id = '${LOOKER_MODEL}:${LOOKER_EXPLORE}'
  `
    return runExampleQuery(sql)
      .then((response) => {
        const refinementExamples = JSON.parse(response[0]['examples'])
        dispatch(setExploreRefinementExamples(refinementExamples))
      })
      .catch((error) => showBoundary(error))
  }

  // get the example prompts
  useEffect(() => {
    getExamplePrompts()
    getRefinementPrompts()
  }, [showBoundary])
}
