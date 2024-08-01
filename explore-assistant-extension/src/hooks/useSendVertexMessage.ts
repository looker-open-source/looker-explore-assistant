import { ExtensionContext } from '@looker/extension-sdk-react'
import { useCallback, useContext } from 'react'
import { useSelector } from 'react-redux'
import CryptoJS from 'crypto-js'
import { RootState } from '../store'
import process from 'process'
import { useErrorBoundary } from 'react-error-boundary'
import { Settings } from 'http2'

import looker_filter_doc from '../documents/looker_filter_doc.md'
import looker_visualization_doc from '../documents/looker_visualization_doc.md'

import { ModelParameters } from '../utils/VertexHelper'
import { BigQueryHelper } from '../utils/BigQueryHelper'
import { ExploreParams } from '../slices/assistantSlice'

const parseJSONResponse = (jsonString: string) => {
  if (jsonString.startsWith('```json') && jsonString.endsWith('```')) {
    jsonString = jsonString.slice(7, -3).trim()
  }

  try {
    return JSON.parse(jsonString)
  } catch (error) {
    return jsonString
  }
}

function formatRow(field: {
  name?: string
  type?: string
  label?: string
  description?: string
  tags?: string[]
}) {
  // Initialize properties with default values if not provided
  const name = field.name || ''
  const type = field.type || ''
  const label = field.label || ''
  const description = field.description || ''
  const tags = field.tags ? field.tags.join(', ') : ''

  // Return a markdown row
  return `| ${name} | ${type} | ${label} | ${description} | ${tags} |`
}

const useSendVertexMessage = () => {
  const { showBoundary } = useErrorBoundary()

  // cloud function
  const VERTEX_AI_ENDPOINT = process.env.VERTEX_AI_ENDPOINT || ''
  const VERTEX_CF_AUTH_TOKEN = process.env.VERTEX_CF_AUTH_TOKEN || ''

  // bigquery
  const VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME =
    process.env.VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME || ''
  const VERTEX_BIGQUERY_MODEL_ID = process.env.VERTEX_BIGQUERY_MODEL_ID || ''

  const { core40SDK } = useContext(ExtensionContext)
  const { dimensions, measures, exploreName, modelName } =
    useSelector((state: RootState) => state.assistant)

  const settings = useSelector<RootState, Settings>(
    (state) => state.assistant.settings,
  )

  const { exploreGenerationExamples, exploreRefinementExamples } = useSelector(
    (state: RootState) => state.assistant.examples,
  )

  const vertexBigQuery = async (
    contents: string,
    parameters: ModelParameters,
  ) => {
    const createSQLQuery = await core40SDK.ok(
      core40SDK.create_sql_query({
        connection_name: VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME,
        sql: BigQueryHelper.generateSQL(
          VERTEX_BIGQUERY_MODEL_ID,
          contents,
          parameters,
        ),
      }),
    )

    if (createSQLQuery.slug) {
      const runSQLQuery: any = await core40SDK.ok(
        core40SDK.run_sql_query(createSQLQuery.slug, 'json'),
      )
      const exploreData = await runSQLQuery[0]['generated_content']

      // clean up the data by removing backticks
      const cleanExploreData = exploreData
        .replace(/```json/g, '')
        .replace(/```/g, '')
        .trim()

      return cleanExploreData
    }
  }

  const vertexCloudFunction = async (
    contents: string,
    parameters: ModelParameters,
  ) => {
    const body = JSON.stringify({
      contents: contents,
      parameters: parameters,
    })

    const signature = CryptoJS.HmacSHA256(body, VERTEX_CF_AUTH_TOKEN).toString()

    const responseData = await fetch(VERTEX_AI_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Signature': signature,
      },

      body: body,
    })
    const response = await responseData.text()
    return response.trim()
  }

  const summarizePrompts = useCallback(
    async (promptList: string[]) => {
      const contents = `
    
      Primer
      ----------
      A user is iteractively asking questions to generate an explore URL in Looker. The user is refining his questions by adding more context. The additional prompts he is adding could have conflicting or duplicative information: in those cases, prefer the most recent prompt. 

      Here are some example prompts the user has asked so far and how to summarize them:

${exploreRefinementExamples
  .map((item) => {
    const inputText = '"' + item.input.join('", "') + '"'
    return `- The sequence of prompts from the user: ${inputText}. The summarized prompts: "${item.output}"`
  })
  .join('\n')}

      Conversation so far
      ----------
      input: ${promptList.map((prompt) => '"' + prompt + '"').join('\n')}
    
      Task
      ----------
      Summarize the prompts above to generate a single prompt that includes all the relevant information. If there are conflicting or duplicative information, prefer the most recent prompt.

      Only return the summary of the prompt with no extra explanatation or text
        
    `
      const response = await sendMessage(contents, {})

      return response
    },
    [exploreRefinementExamples],
  )

  const promptWrapper = (prompt: string) => {
    // wrap the prompt with the current date
    const currentDate = new Date().toLocaleString()
    return `The current date is ${currentDate}
    
    
    ${prompt}
    `
  }

  const isSummarizationPrompt = async (prompt: string) => {
    const contents = `
      Primer
      ----------

      A user is interacting with an agent that is translating questions to a structured URL query based on the following dictionary. The user is refining his questions by adding more context. You are a very smart observer that will look at one such question and determine whether the user is asking for a data summary, or whether they are continuing to refine their question.
  
      Task
      ----------
      Determine if the user is asking for a data summary or continuing to refine their question. If they are asking for a summary, they might say things like:
      
      - summarize the data
      - give me the data
      - data summary
      - tell me more about it
      - explain to me what's going on
      
      The user said:

      ${prompt}

      Output
      ----------
      Return "data summary" if the user is asking for a data summary, and "refining question" if the user is continuing to refine their question. Only output one answer, no more. Only return one those two options. If you're not sure, return "refining question".

    `
    const response = await sendMessage(contents, {})
    return response === 'data summary'
  }

  const summarizeExplore = useCallback(
    async (exploreParams: ExploreParams) => {
      // get the contents of the explore query
      const createQuery = await core40SDK.ok(
        core40SDK.create_query({
          model: modelName,
          view: exploreName,

          fields: exploreParams.fields || [],
          filters: exploreParams.filters || {},
          sorts: exploreParams.sorts || [],
          limit: exploreParams.limit || '1000',
        }),
      )

      const queryId = createQuery.id
      if (queryId === undefined || queryId === null) {
        return 'There was an error!!'
      }
      const result = await core40SDK.ok(
        core40SDK.run_query({
          query_id: queryId,
          result_format: 'md',
        }),
      )

      if (result.length === 0) {
        return 'There was an error!!'
      }

      const contents = `
      Data
      ----------

      ${result}
      
      Task
      ----------
      Summarize the data above
    
    `
      const response = await sendMessage(contents, {})

      const refinedContents = `
      The following text represents summaries of a given dashboard's data. 
        Summaries: ${response}

        Make this much more concise for a slide presentation using the following format. The summary should be a markdown documents that contains a list of sections, each section should have the following details:  a section title, which is the title for the given part of the summary, and key points which a list of key points for the concise summary. Data should be returned in each section, you will be penalized if it doesn't adhere to this format. Each summary should only be included once. Do not include the same summary twice.
        `

      const refinedResponse = await sendMessage(refinedContents, {})
      return refinedResponse
    },
    [exploreName, modelName],
  )

  const generateFilterParams = useCallback(
    async (prompt: string) => {
      // get the filters
      const filterContents = `

   ${looker_filter_doc}
   
   # LookML Definitions
   
   Below is a table of dimensions and measures that can be used to be determine what the filters should be. Pay attention to the dimension type when translating the filters.
   
   | Field Id | Field Type | LookML Type | Label | Description | Tags |
   |------------|------------|-------------|-------|-------------|------|
   ${dimensions.map(formatRow).join('\n')}
   ${measures.map(formatRow).join('\n')}
   
   # Instructions
   
   The user asked the following question:
   
   \`\`\`
   ${prompt}
   \`\`\`
   
   
   Your job is to follow the steps below and generate a JSON object.
   
   * Step 1: Your task is the look at the following data question that the user is asking and determin the filter expression for it. You should return a JSON list of filters to apply. Each element in the list will be a pair of the field id and the filter expression. Your output will look like \` [ { "field_id": "example_view.created_date", "filter_expression": "this year" } ]\`
   * Step 2: verify that you're only using valid expressions for the filter values. If you do not know what the valid expressions are, refer to the table above. If you are still unsure, don't use the filter.
   * Step 3: verify that the field ids are indeed Field Ids from the table. If they are not, you should return an empty dictionary. There should be a period in the field id.
   
   `
      console.log(filterContents)
      const filterResponseInitial = await sendMessage(filterContents, {})

      // check the response
      const filterContentsCheck =
        filterContents +
        `

         # Output
   
         ${filterResponseInitial}
   
         # Instructions
   
         Verify the output, make changes and return the JSON
   
         `
      const filterResponseCheck = await sendMessage(filterContentsCheck, {})
      const filterResponseCheckJSON = parseJSONResponse(filterResponseCheck)

      // Iterate through each filter
      const filterResponseJSON: any = {}

      // Iterate through each filter
      filterResponseCheckJSON.forEach(function (filter: {
        field_id: string
        filter_expression: string
      }) {
        // Check if the field_id already exists in the hash
        if (!filterResponseJSON[filter.field_id]) {
          // If not, create an empty array for this field_id
          filterResponseJSON[filter.field_id] = []
        }
        // Push the filter_expression into the array
        filterResponseJSON[filter.field_id].push(filter.filter_expression)
      })

      console.log('filterResponseInitial', filterResponseInitial)
      console.log('filterResponseCheckJSON', filterResponseCheckJSON)
      console.log('filterResponseJSON', filterResponseJSON)

      return filterResponseJSON
    },
    [dimensions, measures],
  )

  const generateVisualizationParams = async (
    exploreParams: ExploreParams,
    prompt: string,
  ) => {
    const contents = `

    ${looker_visualization_doc}

      # User Request

      ## Prompt

      The user asked the following question:

      \`\`\`
      ${prompt}
      \`\`\`

      ## Explore Definition

      The user is asking for the following explore definition:

      \`\`\`
      ${JSON.stringify(exploreParams)}
      \`\`\`

      ## Determine Visualization JSON

      Based on the question, and on the original question, determine what the visualization config should be. The visualization config should be a JSON object that is compatible with the Looker API run_inline_query function. Only contain values that are different than the defaults. Here is an example:

      \`\`\`
      {
        "type": "looker_column",
      }
      \`\`\`

    `
    const parameters = {
      max_output_tokens: 1000,
    }
    const response = await sendMessage(contents, parameters)
    return parseJSONResponse(response)
  }

  const generateBaseExploreParams = useCallback(
    async (prompt: string) => {
      if (!dimensions.length || !measures.length) {
        showBoundary(new Error('Dimensions or measures are not defined'))
        return
      }
      const currentDateTime = new Date().toISOString()
      const contents = `
      # Context
      
      Your job is to convert a user question in plain language to the JSON payload that we will use to generate a Looker API call to the run_inline_query function.
      
      ## Format of query object
      
      | Field              | Type   | Description                                                                                                                                                                                                                                                                          |
      |--------------------|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
      | model              | string | Model                                                                                                                                                                                                                                                                                |
      | view               | string | Explore Name                                                                                                                                                                                                                                                                         |
      | fields             | string[] | Fields                                                                                                                                                                                                                                                                                |
      | pivots             | string[] | Pivots                                                                                                                                                                                                                                                                                |
      | fill_fields        | string[] | Fill Fields                                                                                                                                                                                                                                                                           |
      | filters            | object | Filters                                                                                                                                                                                                                                                                               |
      | filter_expression  | string | Filter Expression                                                                                                                                                                                                                                                                     |
      | sorts              | string[] | Sorts                                                                                                                                                                                                                                                                                 |
      | limit              | string | Limit                                                                                                                                                                                                                                                                                 |
      | column_limit       | string | Column Limit                                                                                                                                                                                                                                                                          |
      | total              | boolean | Total                                                                                                                                                                                                                                                                                 |
      | row_total          | string | Raw Total                                                                                                                                                                                                                                                                             |
      | subtotals          | string[] | Subtotals                                                                                                                                                                                                                                                                             |
      | vis_config         | object | Visualization configuration properties. These properties are typically opaque and differ based on the type of visualization used. There is no specified set of allowed keys. The values can be any type supported by JSON. A "type" key with a string value is often present, and is used by Looker to determine which visualization to present. Visualizations ignore unknown vis_config properties. |
      | filter_config      | object | The filter_config represents the state of the filter UI on the explore page for a given query. When running a query via the Looker UI, this parameter takes precedence over "filters". When creating a query or modifying an existing query, "filter_config" should be set to null. Setting it to any other value could cause unexpected filtering behavior. The format should be considered opaque. |
      
          
      # LookML Metadata
      
      Model: ${modelName}
      Explore: ${exploreName}
      
      Dimensions Used to group by information (follow the instructions in tags when using a specific field; if map used include a location or lat long dimension;):
      
      | Field Id | Field Type | LookML Type | Label | Description | Tags |
      |------------|------------|-------------|-------|-------------|------|
      ${dimensions.map(formatRow).join('\n')}
                
      Measures are used to perform calculations (if top, bottom, total, sum, etc. are used include a measure):
      
      | Field Id | Field Type | LookML Type | Label | Description | Tags |
      |------------|------------|-------------|-------|-------------|------|
      ${measures.map(formatRow).join('\n')}
          
      # Examples
        Examples Below were taken at a different date. ALL DATE RANGES ARE WRONG COMPARING TO CURRENT DATE.
        (BE CAREFUL WITH DATES, DO NOT OUTPUT THE Examples 1:1,  as changes could happen with timeframes and date ranges)
      ${exploreGenerationExamples
        .map((item) => `input: "${item.input}" ; output: ${item.output}`)
        .join('\n')}
      
      
      Output
      ----------
      
      Return a JSON that is compatible with the Looker API run_inline_query function as per the spec. Here is an example:
      
      {
        "model":"${modelName}",
        "view":"${exploreName}",
        "fields":["category.name","inventory_items.days_in_inventory_tier","products.count"],
        "filters":{"category.name":"socks"},
        "sorts":["products.count desc 0"],
        "limit":"500",
      }
      
      Instructions:
      - choose only the fields in the below lookml metadata
      - prioritize the field description, label, tags, and name for what field(s) to use for a given description
      - generate only one answer, no more.
      - use the Examples for guidance on how to structure the body
      - try to avoid adding dynamic_fields, provide them when very similar example is found in the bottom
      - Always use the provided current date (${currentDateTime}) when generating Looker URL queries that involve TIMEFRAMES.
      - only respond with a JSON object
        
        
      User Request
      ----------
      ${prompt}
      
      `

      const parameters = {
        max_output_tokens: 1000,
      }
      console.log(contents)
      const response = await sendMessage(contents, parameters)
      const responseJSON = parseJSONResponse(response)

      return responseJSON
    },
    [dimensions, measures, exploreGenerationExamples],
  )

  const generateExploreParams = useCallback(
    async (prompt: string) => {
      if (!dimensions.length || !measures.length) {
        showBoundary(new Error('Dimensions or measures are not defined'))
        return
      }

      const [filterResponseJSON, responseJSON ] = await Promise.all([
        generateFilterParams(prompt),
        generateBaseExploreParams(prompt),
      ])

      responseJSON['filters'] = filterResponseJSON
      console.log(responseJSON)

      // get the visualizations
      const visualizationResponseJSON = await generateVisualizationParams(
        responseJSON,
        prompt,
      )
      console.log(visualizationResponseJSON)

      //responseJSON['vis_config'] = visualizationResponseJSON

      return responseJSON
    },
    [dimensions, measures, exploreGenerationExamples, settings],
  )

  const sendMessage = async (message: string, parameters: ModelParameters) => {
    const wrappedMessage = promptWrapper(message)
    try {
      if (
        VERTEX_AI_ENDPOINT &&
        VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME &&
        VERTEX_BIGQUERY_MODEL_ID
      ) {
        throw new Error(
          'Both Vertex AI and BigQuery are enabled. Please only enable one',
        )
      }

      let response = ''
      if (VERTEX_AI_ENDPOINT) {
        response = await vertexCloudFunction(wrappedMessage, parameters)
      } else if (
        VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME &&
        VERTEX_BIGQUERY_MODEL_ID
      ) {
        response = await vertexBigQuery(wrappedMessage, parameters)
      } else {
        throw new Error('No Vertex AI or BigQuery connection found')
      }

      if (response.startsWith('```json') && response.endsWith('```')) {
        response = response.slice(7, -3).trim()
      }

      return response
    } catch (error) {
      showBoundary(error)
    }

    return ''
  }

  return {
    generateExploreParams,
    generateBaseExploreParams,
    generateFilterParams,
    generateVisualizationParams,
    sendMessage,
    summarizePrompts,
    isSummarizationPrompt,
    summarizeExplore,
  }
}

export default useSendVertexMessage
