import { ExtensionContext } from '@looker/extension-sdk-react'
import { useCallback, useContext } from 'react'
import { useSelector } from 'react-redux'
import { UtilsHelper } from '../utils/Helper'
import CryptoJS from 'crypto-js'
import { RootState } from '../store'
import process from 'process'
import { useErrorBoundary } from 'react-error-boundary'
import { AssistantState } from '../slices/assistantSlice'

const unquoteResponse = (response: string | null | undefined) => {
  if(!response) {
    return ''
  }
  return response
    .substring(response.indexOf('fields='))
    .replace(/^`+|`+$/g, '')
    .trim()
}

interface ModelParameters {
  max_output_tokens?: number
}

const generateSQL = (
  model_id: string,
  prompt: string,
  parameters: ModelParameters,
) => {
  const escapedPrompt = UtilsHelper.escapeQueryAll(prompt)
  const subselect = `SELECT '` + escapedPrompt + `' AS prompt`

  return `
  
    SELECT ml_generate_text_llm_result AS generated_content
    FROM
    ML.GENERATE_TEXT(
        MODEL \`${model_id}\`,
        (
          ${subselect}
        ),
        STRUCT(
        0.05 AS temperature,
        1024 AS max_output_tokens,
        0.98 AS top_p,
        TRUE AS flatten_json_output,
        1 AS top_k)
      )
  
      `
}

function formatContent(field: {
  name?: string
  type?: string
  label?: string
  description?: string
  tags?: string[]
}) {
  let result = ''
  if (field.name) result += 'name: ' + field.name
  if (field.type) result += (result ? ', ' : '') + 'type: ' + field.type
  if (field.label) result += (result ? ', ' : '') + 'label: ' + field.label
  if (field.description)
    result += (result ? ', ' : '') + 'description: ' + field.description
  if (field.tags && field.tags.length)
    result += (result ? ', ' : '') + 'tags: ' + field.tags.join(', ')

  return result
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
  const { settings, examples, currentExplore} =
    useSelector((state: RootState) => state.assistant as AssistantState)

  const currentExploreKey = currentExplore.exploreKey
  const exploreRefinementExamples = examples.exploreRefinementExamples[currentExploreKey]
  const trustedDashboards = examples.trustedDashboards[currentExploreKey]

  const vertextBigQuery = async (
    contents: string,
    parameters: ModelParameters,
  ) => {
    const createSQLQuery = await core40SDK.ok(
      core40SDK.create_sql_query({
        connection_name: VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME,
        sql: generateSQL(VERTEX_BIGQUERY_MODEL_ID, contents, parameters),
      }),
    )

    if (createSQLQuery.slug) {
      const runSQLQuery = await core40SDK.ok(
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

  const vertextCloudFunction = async (
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

${exploreRefinementExamples && exploreRefinementExamples
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
    async (exploreQueryArgs: string) => {
      const params = new URLSearchParams(exploreQueryArgs)

      // Initialize an object to construct the query
      const queryParams: {
        fields: string[]
        filters: Record<string, string>
        sorts: string[]
        limit: string
      } = {
        fields: [],
        filters: {},
        sorts: [],
        limit: '',
      }

      // Iterate over the parameters to fill the query object
      params.forEach((value, key) => {
        if (key === 'fields') {
          queryParams.fields = value.split(',')
        } else if (key.startsWith('f[')) {
          const filterKey = key.match(/\[(.*?)\]/)?.[1]
          if (filterKey) {
            queryParams.filters[filterKey] = value
          }
        } else if (key === 'sorts') {
          queryParams.sorts = value.split(',')
        } else if (key === 'limit') {
          queryParams.limit = value
        }
      })

      console.log(params)

      // get the contents of the explore query
      const createQuery = await core40SDK.ok(
        core40SDK.create_query({
          model: currentExplore.modelName,
          view: currentExplore.exploreId,

          fields: queryParams.fields || [],
          filters: queryParams.filters || {},
          sorts: queryParams.sorts || [],
          limit: queryParams.limit || '1000',
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

  const generateExploreUrl = useCallback(
    async (
      prompt: string,
      dimensions: any[],
      measures: any[],
      exploreGenerationExamples: any[],
      trustedDashboards: any[],
    ) => {
      try {
        const contents = `
            Context
            ----------

            You are a developer who would transalate questions to a structured Looker URL query based on the following instructions.

            Instructions:
              - choose only the fields in the below lookml metadata
              - prioritize the field description, label, tags, and name for what field(s) to use for a given description
              - generate only one answer, no more.
              - use the Examples (at the bottom) for guidance on how to structure the Looker url query
              - try to avoid adding dynamic_fields, provide them when very similar example is found in the bottom
              - never respond with sql, always return an looker explore url as a single string
              - response should start with fields= , as in the Examples section at the bottom  

            LookML Metadata
            ----------

            Dimensions Used to group by information (follow the instructions in tags when using a specific field; if map used include a location or lat long dimension;):

          ${dimensions.map(formatContent).join('\n')}

            Measures are used to perform calculations (if top, bottom, total, sum, etc. are used include a measure):

          ${measures.map(formatContent).join('\n')}

            Trusted dashboards include configuration for the most important, verified, and accurate dashboards. If a dashboard is trusted, it should be used as a reference for the user's query. 
            Nomenclature and proper naming for metrics can be derived from these trusted dashboard. They are in Looker LookML dashboard yaml-like format. There may be 1 or more trusted dashboards.

          ${trustedDashboards.map((item) => item).join('\n')}

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
            
            Example input and outputs:
            ----------

          ${exploreGenerationExamples && exploreGenerationExamples
            .map((item) => `input: "${item.input}" ; output: ${item.output}`)
            .join('\n')}

            Input
            ----------
            ${prompt}

            Output
            ----------
        `
        const parameters = {
          max_output_tokens: 1000,
        }
        console.log(contents)
        const response = await sendMessage(contents, parameters)

        const cleanResponse = unquoteResponse(response)
        console.log(cleanResponse)

        let toggleString = '&toggle=dat,pik,vis'
        if (settings['show_explore_data'].value) {
          toggleString = '&toggle=pik,vis'
        }

        const newExploreUrl = cleanResponse + toggleString

        return newExploreUrl
      } catch (error) {
        console.error(
          'Error waiting for data (lookml fields & training examples) to load:',
          error,
        )
        showBoundary({
          message:
            'Error waiting for data (lookml fields & training examples) to load:',
          error,
        })
        return
      }
    },
    [settings],
  )

  const sendMessage = async (message: string, parameters: ModelParameters) => {
    try {
      let response = ''
      if (VERTEX_AI_ENDPOINT) {
        response = await vertextCloudFunction(message, parameters)
      }

      if (VERTEX_BIGQUERY_LOOKER_CONNECTION_NAME && VERTEX_BIGQUERY_MODEL_ID) {
        response = await vertextBigQuery(message, parameters)
      }

      return response
    } catch (error) {
      showBoundary(error)
      return
    }
  }

  return {
    generateExploreUrl,
    sendMessage,
    summarizePrompts,
    isSummarizationPrompt,
    summarizeExplore,
  }
}

export default useSendVertexMessage
