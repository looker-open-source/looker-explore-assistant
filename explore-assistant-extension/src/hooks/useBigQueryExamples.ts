import { useContext, useEffect } from 'react'
import { useDispatch } from 'react-redux'
import {
  setExploreGenerationExamples,
  setExploreRefinementExamples,
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

  // get the example prompts
  useEffect(() => {
      getExamplePrompts()
      getRefinementPrompts()
  }, [showBoundary])
}
