import { useContext, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../store'
import {
  setExploreGenerationExamples,
  setExploreRefinementExamples,
  setExploreSamples,
  setExplores,
  setBigQueryExamplesLoaded
} from '../slices/assistantSlice'

import { ExtensionContext } from '@looker/extension-sdk-react'
import process from 'process'
import { useErrorBoundary } from 'react-error-boundary'

export const useBigQueryExamples = () => {
  const { exploreName, modelName} = useSelector(
    (state: RootState) => state.assistant,
  )
  const connectionName =
    process.env.BIGQUERY_EXAMPLE_PROMPTS_CONNECTION_NAME || ''
  const LOOKER_MODEL = modelName || process.env.LOOKER_MODEL || ''
  const LOOKER_EXPLORE = exploreName || process.env.LOOKER_EXPLORE || ''
  const datasetName =
    process.env.BIGQUERY_EXAMPLE_PROMPTS_DATASET_NAME || 'explore_assistant'

  const dispatch = useDispatch()
  const { showBoundary } = useErrorBoundary();

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
    } catch(error) {
      showBoundary(error)
      throw new Error('error')
    }
  }

  const getExplores = async () => {
    const sql = `
      SELECT DISTINCT
        explore_id
      FROM
        \`${datasetName}.explore_assistant_examples\`
    `
    return runExampleQuery(sql).then((response) => {
      dispatch(setExplores(response))
    }).catch((error) => showBoundary(error))
  }

  const getExamplePrompts = async () => {
    const sql = `
      SELECT
          examples
      FROM
        \`${datasetName}.explore_assistant_examples\`
        WHERE explore_id = '${LOOKER_MODEL}:${LOOKER_EXPLORE}'
    `
    return runExampleQuery(sql).then((response) => {
      const generationExamples = JSON.parse(response[0]['examples'])
      dispatch(setExploreGenerationExamples(generationExamples))
    }).catch((error) => showBoundary(error))
  }

  const getRefinementPrompts = async () => {
    const sql = `
    SELECT
        examples
    FROM
      \`${datasetName}.explore_assistant_refinement_examples\`
      WHERE explore_id = '${LOOKER_MODEL}:${LOOKER_EXPLORE}'
  `
    return runExampleQuery(sql).then((response) => {
      const refinementExamples = JSON.parse(response[0]['examples'])
      dispatch(setExploreRefinementExamples(refinementExamples))
    }).catch((error) => showBoundary(error))
  }

  const getSamples = async () => {
    const sql = `
      SELECT
          explore_id,
          samples
      FROM
        \`${datasetName}.explore_assistant_samples\`
    `
    return runExampleQuery(sql).then((response) => {
      console.log(response)
      const generationSamples = response
      dispatch(setExploreSamples(generationSamples))
    }).catch((error) => showBoundary(error))
  }

  // only run once
  useEffect(() => {
    getExplores()
    getSamples()
  },[showBoundary])

  // get the example prompts provide completion status
  useEffect(() => {
    dispatch(setBigQueryExamplesLoaded(false))
    Promise.all([getExamplePrompts(), getRefinementPrompts()])
      .then(() => {
        dispatch(setBigQueryExamplesLoaded(true))
      })
      .catch((error) => {
        showBoundary(error)
        dispatch(setBigQueryExamplesLoaded(true))
      })
  }, [modelName, exploreName, showBoundary])
}
