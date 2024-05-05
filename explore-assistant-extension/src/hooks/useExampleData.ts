import { useContext, useEffect, useState } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import process from 'process'

export const useExampleData = () => {
  const connectionName =
    process.env.VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME || ''
  const LOOKER_MODEL = process.env.LOOKER_MODEL || ''
  const LOOKER_EXPLORE = process.env.LOOKER_EXPLORE || ''
  const datasetName =
    process.env.BIGQUERY_EXAMPLE_PROMPTS_DATASET_NAME || 'explore_assistant'
  const [data, setData] = useState<any>([])
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
       examples
   FROM
     \`${datasetName}.explore_assistant_examples\`
    WHERE explore_id = '${LOOKER_MODEL}:${LOOKER_EXPLORE}'
 `
    return runExampleQuery(sql).then((response) => {
        return response[0]['examples']
    })
  }

  useEffect(() => {
      getExamplePrompts().then((assistantExamples) => {
        const parsedExamples = JSON.parse(assistantExamples)
        setData(parsedExamples)
      })

  }, [])

  return { examples: data }
}
