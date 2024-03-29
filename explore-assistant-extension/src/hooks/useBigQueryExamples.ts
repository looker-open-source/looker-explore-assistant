import { useContext, useEffect } from 'react'
import { useDispatch } from 'react-redux'
import {
  setExploreGenerationExamples,
  setExploreRefinementExamples,
} from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'
import process from 'process'

export const useBigQueryExamples = () => {
  const connectionName =
    process.env.BIGQUERY_EXAMPLE_PROMPTS_CONNECTION_NAME || ''
  const datasetName = process.env.BIGQUERY_EXAMPLE_PROMPTS_DATASET_NAME || ''
  const dispatch = useDispatch()

  const { core40SDK } = useContext(ExtensionContext)

  const runExampleQuery = async (sql: string) => {
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
  }

  const getExamplePrompts = async () => {
    const sql = `
   SELECT
       input_prompt
     , output_query_args
   FROM
     \`${datasetName}.explore_generation_example_prompts\`
 `
    const examples = await runExampleQuery(sql)
    dispatch(setExploreGenerationExamples(examples))
  }

  const getRefinementPrompts = async () => {
    const sql = `
    SELECT
        TO_JSON_STRING(prompt_list) as prompt_list
      , output_prompt
    FROM
      \`${datasetName}.explore_refinement_example_prompts\`
  `
     const examples = await runExampleQuery(sql)
     const parsedExamples = examples.map((example: any) => {

         return {
            prompt_list: JSON.parse(example.prompt_list),
            output_prompt: example.output_prompt
         }
      })
     dispatch(setExploreRefinementExamples(parsedExamples))
  }

  // get the example prompts
  useEffect(() => {
    getExamplePrompts()
    getRefinementPrompts()
  }, [])
}
