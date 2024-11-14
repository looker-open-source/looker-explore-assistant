import { ExtensionContext } from '@looker/extension-sdk-react'
import { useCallback, useContext } from 'react'
import { useSelector } from 'react-redux'
import CryptoJS from 'crypto-js'
import { RootState } from '../store'
import process from 'process'
import { useErrorBoundary } from 'react-error-boundary'
import { AssistantState } from '../slices/assistantSlice'

import looker_filter_doc from '../documents/looker_filter_doc.md'
import looker_visualization_doc from '../documents/looker_visualization_doc.md'
import looker_filters_interval_tf from '../documents/looker_filters_interval_tf'

import { ModelParameters } from '../utils/VertexHelper'
import { BigQueryHelper } from '../utils/BigQueryHelper'
import { ExploreParams } from '../slices/assistantSlice'
import { ExploreFilterValidator, FieldType } from '../utils/ExploreFilterHelper'


const parseJSONResponse = (jsonString: string | null | undefined) => {
  if(!jsonString) {
    return ''
  }
  
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
  const { settings, examples, currentExplore } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )

  const currentExploreKey = currentExplore.exploreKey
  const exploreRefinementExamples =
    examples.exploreRefinementExamples[currentExploreKey]

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

${
  exploreRefinementExamples &&
  exploreRefinementExamples
    .map((item) => {
      const inputText = '"' + item.input.join('", "') + '"'
      return `- The sequence of prompts from the user: ${inputText}. The summarized prompts: "${item.output}"`
    })
    .join('\n')
}

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

      // get the contents of the explore query
      const createQuery = await core40SDK.ok(
        core40SDK.create_query({
          model: currentExplore.modelName,
          view: currentExplore.exploreId,

          fields: exploreParams.fields || [],
          filters: filters,
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
    [currentExplore],
  )
  const generateFilterParams = useCallback(
    async (prompt: string, dimensions: any[], measures: any[]) => {
      // get the filters
      const filterContents = `
  
     ${looker_filter_doc}
     
     # LookML Definitions
     
     Below is a table of dimensions and measures that can be used to determine what the filters should be. Pay attention to the dimension type when translating the filters.
     
     | Field Id | Field Type | LookML Type | Label | Description | Tags |
     |------------|------------|-------------|-------|-------------|------|
     ${dimensions.map(formatRow).join('\n')}
     ${measures.map(formatRow).join('\n')}

    Here is some documentation on how intervals and timeframes are applied in Looker

     ${looker_filters_interval_tf}
     
     # Instructions
     
     The user asked the following question:
     
     \`\`\`
     ${prompt}
     \`\`\`
     
     
     Your job is to follow the steps below and generate a JSON object.
     
     * Step 1: Your task is the look at the following data question that the user is asking and determine the filter expression for it. You should return a JSON list of filters to apply. Each element in the list will be a pair of the field id and the filter expression. Your output will look like \`[ { "field_id": "example_view.created_date", "filter_expression": "this year" } ]\`
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

      // Validate each filter
      filterResponseCheckJSON.forEach(function (filter: {
        field_id: string
        filter_expression: string
      }) {
        const field =
          dimensions.find((d) => d.name === filter.field_id) ||
          measures.find((m) => m.name === filter.field_id)

        if (!field) {
          console.log(`Invalid field: ${filter.field_id}`)
          return
        }

        console.log(field)

        const isValid = ExploreFilterValidator.isFilterValid(
          field.type as FieldType,
          filter.filter_expression,
        )

        if (!isValid) {
          console.log(
            `Invalid filter expression for field ${filter.field_id}: ${filter.filter_expression}`,
          )
          return
        }

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
    [],
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
    async (
      prompt: string,
      dimensions: any[],
      measures: any[],
      exploreGenerationExamples: any[],
    ) => {
      if (!dimensions.length || !measures.length) {
        showBoundary(new Error('Dimensions or measures are not defined'))
        return
      }
      const currentDateTime = new Date().toISOString()

      const parseLookerURL = (url: string): { [key: string]: any } => {
        // Split URL and extract model & explore
        const urlSplit = url.split("?");
        let model = ""
        let explore = ""
        let queryString = ""
        if (urlSplit.length == 2) {
          const rootURL = urlSplit[0]
          queryString = urlSplit[1]
          const rootURLElements = rootURL.split("/");
          model = rootURLElements[rootURLElements.length - 2];
          explore = rootURLElements[rootURLElements.length - 1];
        }
        else if (urlSplit.length == 1) {
          model = "tbd"
          explore = "tbd"
          queryString = urlSplit[0]
        }
        // Initialize lookerEncoding object
        const lookerEncoding: { [key: string]: any } = {};
        lookerEncoding['model'] = ""
        lookerEncoding['explore'] = ""
        lookerEncoding['fields'] = []
        lookerEncoding['pivots'] = []
        lookerEncoding['fill_fields'] = []
        lookerEncoding['filters'] = {}
        lookerEncoding['filter_expression'] = null
        lookerEncoding['sorts'] = []
        lookerEncoding['limit'] = 500
        lookerEncoding['column_limit'] = 50
        lookerEncoding['total'] = null
        lookerEncoding['row_total'] = null
        lookerEncoding['subtotals'] = null
        lookerEncoding['vis'] = []
        // Split query string and iterate key-value pairs
        const keyValuePairs = queryString.split("&");
        for (const qq of keyValuePairs) {
          const [key, value] = qq.split('=');
          console.log(qq)
          lookerEncoding['model'] = model
          lookerEncoding['explore'] = explore
          switch (key) {
            case "fields":
            case "pivots":
            case "fill_fields":
            case "sorts":
              lookerEncoding[key] = value.split(",");
              break;
            case "filter_expression":
            case "total":
            case "row_total":
            case "subtotals":
              lookerEncoding[key] = value;
              break;
            case "limit":
            case "column_limit":
              lookerEncoding[key] = parseInt(value);
              break;
            case "vis":
              lookerEncoding[key] = JSON.parse(decodeURIComponent(value));
              break;
            default:
              if (key.startsWith("f[")) {
                const filterKey = key.slice(2, -1);
                lookerEncoding.filters[filterKey] = value;
              } else if (key.includes(".")) {
                const path = key.split(".");
                let currentObject = lookerEncoding;
                for (let i = 0; i < path.length - 1; i++) {
                  const segment = path[i];
                  if (!currentObject[segment]) {
                    currentObject[segment] = {};
                  }
                  currentObject = currentObject[segment];
                }
                currentObject[path[path.length - 1]] = value;
              }
          }
        }
        return lookerEncoding;
      };






let exampleText = ''
if(exploreGenerationExamples && exploreGenerationExamples.length > 0) {
    exampleText = exploreGenerationExamples.map((item) => `input: "${item.input}" ; output: ${JSON.stringify(parseLookerURL(item.output))}`).join('\n')
}      

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
      
      Model: ${currentExplore.modelName}
      Explore: ${currentExplore.exploreId}
      
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
      ${exampleText}
      
      
      Output
      ----------
      
      Return a JSON that is compatible with the Looker API run_inline_query function as per the spec. Here is an example:
      
      {
        "model":"${currentExplore.modelName}",
        "view":"${currentExplore.exploreId}",
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
        

      
            Looker date filtering allows for English phrases to be used instead of SQL date functions.
            Basic structure of date and time filters
            For the following examples:

            {n} is an integer.
            {interval} is a time increment such as hours, days, weeks, or months.

            The phrasing you use determines whether the {interval} will include partial time periods or only complete time periods. For example, the expression 3 days includes the current, partial day as well as the prior two days. The expression 3 days ago for 3 days includes the previous three complete days and excludes the current, partial day. See the Relative Dates section for more information.

            {time} can specify a time formatted as either YYYY-MM-DD HH:MM:SS or YYYY/MM/DD HH:MM:SS, or a date formatted as either YYYY-MM-DD or YYYY/MM/DD. When using the form YYYY-MM-DD, be sure to include both digits for the month and day, for example, 2016-01. Truncating a month or day to a single digit is interpreted as an offset, not a date. For example, 2016-1 is interpreted as 2016 minus one year, or 2015.

            These are all the possible combinations of date filters:

            Combination	Example	Notes
            this {interval}	this month	You can use this week, this month, this quarter, or this year. Note that this day isn't supported. If you want to get data from the current day, you can use 'today'.
            {n} {interval} = 3 days	
            {n} {interval} ago = 3 days ago	
            {n} {interval} ago for {n} {interval} = 3 months ago for 2 days	
            before {n} {interval} ago = 	before 3 days ago	
            before {time}	= before 2018-01-01 12:00:00	before is not inclusive of the time you specify. The expression before 2018-01-01 will return data from all dates before 2018-01-01, but it won't return data from 2018-01-01.
            after {time} =	after 2018-10-05	after is inclusive of the time you specify. So, the expression after 2018-10-05 will return data from 2018-10-05 and all dates later than 2018-10-05.
            {time} to {time} = 2018-05-18 12:00:00 to 2018-05-18 14:00:00	The initial time value is inclusive but the latter time value is not. So the expression 2018-05-18 12:00:00 to 2018-05-18 14:00:00 will return data with the time "2018-05-18 12:00:00" through "2018-05-18 13:59:59".
            this {interval} to {interval}	= this year to second	The beginning of each interval is used. For example, the expression this year to second returns data from the beginning of the year the query is run through to the beginning of the second the query is run. this week to day returns data from the beginning of the week the query is run through to the beginning of the day the query is run.
            {time} for {n} {interval}	= 2018-01-01 12:00:00 for 3 days	
            today	= today	
            yesterday	= yesterday	
            tomorrow = tomorrow	
            {day of week} =	Monday	Specifying a day of week with a Dimension Group Date field returns the most recent date that matches the specified day of week. For example, the expression Dimension Group Date matches (advanced) Monday returns the most recent Monday.
            You can also use {day of week} with the before and after keywords in this context. For example, the expression Dimension Group Date matches (advanced) after Monday returns the most recent Monday and everything after the most recent Monday. The expression Dimension Group Date matches (advanced) before Monday returns every day before the most recent Monday, but it doesn't return the most recent Monday.
            Specifying a day of the week with a Dimension Group Day of Week field returns every day that matches the specified day of week. So the expression Dimension Group Day of Week matches (advanced) Monday returns every Monday.
            next {week, month, quarter, fiscal quarter, year, fiscal year}	next week	The next keyword is unique in that it requires one of the intervals listed previously and won't work with other intervals.
            {n} {interval} from now =	3 days from now	
            {n} {interval} from now for {n} {interval} = 3 days from now for 2 weeks	
            Date filters can also be combined together:

            To get OR logic: Type multiple conditions into the same filter, separated by commas. For example, today, 7 days ago means "today or 7 days ago".
            To get AND logic: Type your conditions, one by one, into multiple date or time filters. For example, you could put after 2014-01-01 into a Created Date filter, then put before 2 days ago into a Created Time filter. This would mean "January 1st, 2014 and after, and before 2 days ago".

            Absolute dates
            Absolute date filters use the specific date values to generate query results. These are useful when creating queries for specific date ranges.

            Example	Description
            2018/05/29	= sometime on 2018/05/29
            2018/05/10 for 3 days =	from 2018/05/10 00:00:00 through 2018/05/12 23:59:59
            after 2018/05/10	= 2018/05/10 00:00:00 and after
            before 2018/05/10	= before 2018/05/10 00:00:00
            2018/05	= within the entire month of 2018/05
            2018/05 for 2 months	= within the entire months of 2018/05 and 2018/06
            2018/05/10 05:00 for 5 hours = from 2018/05/10 05:00:00 through 2018/05/10 09:59:59
            2018/05/10 for 5 months	= from 2018/05/10 00:00:00 through 2018/10/09 23:59:59
            2018 = entire year of 2018 (2018/01/01 00:00:00 through 2018/12/31 23:59:59)
            FY2018 =	entire fiscal year starting in 2018 (if your Looker developers have specified that your fiscal year starts in April then this is 2018/04/01 00:00 through 2019/03/31 23:59)
            FY2018-Q1	= first quarter of the fiscal year starting in 2018 (if your Looker developers have specified that your fiscal year starts in April then this is 2018/04/01 00:00:00 through 2018/06/30 23:59:59)

            Relative dates
            Relative date filters allow you to create queries with rolling date values relative to the current date. These are useful when creating queries that update each time you run the query.

            For all of the following examples, assume today is Friday, 2018/05/18 18:30:02. In Looker, weeks start on Monday unless you change that setting with week_start_day.


            Seconds
            Example	= Description
            1 second = the current second (2018/05/18 18:30:02)
            60 seconds = 60 seconds ago for 60 seconds (2018/05/18 18:29:02 through 2018/05/18 18:30:01)
            60 seconds ago for 1 second =	60 seconds ago for 1 second (2018/05/18 18:29:02)

            Minutes
            Example	= Description
            1 minute = the current minute (2018/05/18 18:30:00 through 18:30:59)
            60 minutes = 60 minutes ago for 60 minutes (2018/05/18 17:31:00 through 2018/05/18 18:30:59)
            60 minutes ago for 1 minute = 60 minutes ago for 1 minute (2018/05/18 17:30:00 through 2018/05/18 17:30:59)

            Hours
            Example =	Description
            1 hour = the current hour (2018/05/18 18:00 through 2018/05/18 18:59)
            24 hours =	the same hour of day that was 24 hours ago for 24 hours (2018/05/17 19:00 through 2018/05/18 18:59)
            24 hours ago for 1 hour =	the same hour of day that was 24 hours ago for 1 hour (2018/05/17 18:00 until 2018/05/17 18:59)

            Days
            Example	= Description
            today	= the current day (2018/05/18 00:00 through 2018/05/18 23:59)
            2 days =	all of yesterday and today (2018/05/17 00:00 through 2018/05/18 23:59)
            1 day ago =	just yesterday (2018/05/17 00:00 until 2018/05/17 23:59)
            7 days ago for 7 days =	the last complete 7 days (2018/05/11 00:00 until 2018/05/17 23:59)
            today for 7 days = the current day, starting at midnight, for 7 days into the future (2018/05/18 00:00 until 2018/05/24 23:59)
            last 3 days	= 2 days ago through the end of the current day (2018/05/16 00:00 until 2018/05/18 23:59)
            7 days from now =	7 days in the future (2018/05/18 00:00 until 2018/05/25 23:59)

            Weeks
            Example	Description
            1 week = top of the current week going forward (2018/05/14 00:00 through 2018/05/20 23:59)
            this week	= top of the current week going forward (2018/05/14 00:00 through 2018/05/20 23:59)
            before this week = anytime until the top of this week (before 2018/05/14 00:00)
            after this week	= anytime after the top of this week (2018/05/14 00:00 and later)
            next week	= the following Monday going forward 1 week (2018/05/21 00:00 through 2018/05/27 23:59)
            2 weeks	= a week ago Monday going forward (2018/05/07 00:00 through 2018/05/20 23:59)
            last week	= synonym for "1 week ago"
            1 week ago = a week ago Monday going forward 1 week (2018/05/07 00:00 through 2018/05/13 23:59)

            Months
            Example	= Description
            1 month	= the current month (2018/05/01 00:00 through 2018/05/31 23:59)
            this month = synonym for "0 months ago" (2018/05/01 00:00 through 2018/05/31 23:59)
            2 months = the past two months (2018/04/01 00:00 through 2018/05/31 23:59)
            last month = all of 2018/04
            2 months ago = all of 2018/03
            before 2 months ago =	all time before 2018/03/01
            next month = all of 2018/06
            2 months from now	= all of 2018/07
            6 months from now for 3 months =	2018/11 through 2019/01

            Quarters
            Example	= Description
            1 quarter	= the current quarter (2018/04/01 00:00 through 2018/06/30 23:59)
            this quarter = synonym for "0 quarters ago" (2018/04/01 00:00 through 2018/06/30 23:59)
            2 quarters = the past two quarters (2018/01/01 00:00 through 2018/06/30 23:59)
            last quarter = all of Q1 (2018/01/01 00:00 through 2018/03/31 23:59)
            2 quarters ago = all of Q4 of last year (2017/010/01 00:00 through 2017/12/31 23:59)
            before 2 quarters ago =	all time before Q4 of last year
            next quarter = all of the following quarter (2018/07/01 00:00 through 2018/09/30 23:59)
            2018-07-01 for 1 quarter = all of Q3 (2018/07/01 00:00 through 2018/09/30 23:59)
            2018-Q4	= all of Q4 (2018/10/01 00:00 through 2018/12/31 23:59)
            Note: If your Looker developers have specified using a fiscal year then you can type fiscal in these expressions to use a fiscal quarter instead of a calendar quarter. For example, you can use last fiscal quarter.

            Years
            Example	= Description
            1 year = all of the current year (2018/01/01 00:00 through 2018/12/31 23:59)
            this year =	all of the current year (2018/01/01 00:00 through 2018/12/31 23:59)
            next year	= all of the following year (2019/01/01 00:00 through 2019/12/31 23:59)
            2 years = the past two years (2017/01/01 00:00 through 2018/12/31 23:59)
            last year	= all of 2017
            2 years ago	= all of 2016
            before 2 years ago = all time before 2016/01/01 (does not include any days between 2016/01/01 and 2016/05/18)

            End date documentation.

            Begin Number Filters documentation.
          Filters on numbers support both natural language expressions (for example, 3 to 10) and relational operators (for example, >20). Looker supports the OR operator to express multiple filter ranges (for example, 3 to 10 OR 30 to 100). The AND operator can be used to express numeric ranges with relational operators (for example, >=3 AND <=10) to specify a range. Filters on numbers can also use algebraic interval notation to filter numeric fields.
          Note: The syntax for numeric filter expressions using NOT may not be intuitive. If the first filter condition contains a NOT, and no other filter conditions contain a NOT, then all of the filter conditions will be negated. See the following examples for more information.

          Examples:
          - 5: is exactly 5
          - NOT 5: <>5 or !=5, is any value but exactly 5
          - 1, 3, 5, 7: is one of the values 1, 3, 5, or 7, exactly
          - NOT 66, 99, 4: is not one of the values 66, 99, or 4, exactly
          - >1 AND <100, NOT 2: is greater than 1 and less than 100, is not 2
          - NOT >1, 2, <100: is less than or equal to 1, is not 2, and is greater than or equal to 100 (Looker recognizes that this is an impossible condition, and will instead write the SQL IS NULL)
          - 5, NOT 6, NOT 7: is 5, is not 6 or 7
          - 5.5 to 10: >=5.5 AND <=10, is 5.5 or greater but also 10 or less
          - NOT 3 to 80.44: <3 OR >80.44, is less than 3 or greater than 80.44
          - 1 to: >=1, is 1 or greater
          - 10: <=10, is 10 or less
          - >10 AND <=20 OR 90: is greater than 10 and less than or equal to 20, or is 90 exactly
          - >=50 AND <=100 OR >=500 AND <=1000: is between 50 and 100, inclusive, or between 500 and 1000, inclusive
          - NULL: has no data in it (when it is used as part of a LookML filter expression, place NULL in quotes, as shown on the filters documentation page)
          - NOT NULL: has some data in it (when it is used as part of a LookML filter expression, place NOT NULL in quotes, as shown on the filters documentation page)
          - (1, 7): interpreted as 1 < x < 7 where the endpoints aren't included. While this notation resembles an ordered pair, in this context it refers to the interval upon which you are working.
          - [5, 90]: interpreted as 5 <= x <= 90 where the endpoints are included
          - (12, 20]: interpreted as 12 < x <= 20 where 12 is not included, but 20 is included
          - [12, 20): interpreted as 12 <= x < 20 where 12 is included, but 20 is not included
          - (500, inf): interpreted as x > 500 where 500 is not included and infinity is always expressed as being "open" (not included). inf may be omitted and (500, inf) may be written as (500,)
          - (-inf, 10]: interpreted as x <= 10 where 10 is included and infinity is always expressed as being "open" (not included). inf may be omitted and (-inf, 10] may be written as (,10]
          - [0,9],[20,29]: the numbers between 0 and 9 inclusive or 20 to 29 inclusive
          - [0,10],20: 0 to 10 inclusive or 20
          - NOT (3,12): interpreted as x < 3 and x > 12
            End Number Filters documentation.
        
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
    [currentExplore],
  )

  const generateExploreParams = useCallback(
    async (
      prompt: string,
      dimensions: any[],
      measures: any[],
      exploreGenerationExamples: any[],
    ) => {
      if (!dimensions.length || !measures.length) {
        showBoundary(new Error('Dimensions or measures are not defined'))
        return
      }

      const [filterResponseJSON, responseJSON] = await Promise.all([
        generateFilterParams(prompt, dimensions, measures),
        generateBaseExploreParams(prompt, dimensions, measures, exploreGenerationExamples),
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
    [settings],
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
      return
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
