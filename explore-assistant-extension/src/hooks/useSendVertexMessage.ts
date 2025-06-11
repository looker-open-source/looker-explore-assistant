import { ExtensionContext } from '@looker/extension-sdk-react'
import { useCallback, useContext } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../store'
import { useErrorBoundary } from 'react-error-boundary'
import { AssistantState, setVertexTestSuccessful } from '../slices/assistantSlice'

import looker_simplified_reference from '../documents/looker_simplified_reference.md'

import { ModelParameters } from '../utils/VertexHelper'
import { ExploreParams } from '../slices/assistantSlice'
import { ExploreFilterValidator, FieldType } from '../utils/ExploreFilterHelper'


const parseJSONResponse = (jsonString: string | null | undefined) => {
  if (typeof jsonString !== 'string') {
    console.log('parseJSONResponse: input is not a string', jsonString)
    return {}
  }

  console.log('parseJSONResponse raw input:', jsonString)
  
  // Handle different code block formats
  if (jsonString.includes('```')) {
    // Case: ```json...``` format
    if (jsonString.includes('```json')) {
      const match = jsonString.match(/```json\s*([\s\S]*?)\s*```/)
      if (match && match[1]) {
        jsonString = match[1].trim()
      }
    } 
    // Case: ```...``` format (without language specifier)
    else {
      const match = jsonString.match(/```\s*([\s\S]*?)\s*```/)
      if (match && match[1]) {
        jsonString = match[1].trim()
      }
    }
  }

  // Try to find any valid JSON object in the string
  const possibleJsonMatch = jsonString.match(/(\{[\s\S]*\})/m)
  if (possibleJsonMatch && possibleJsonMatch[1]) {
    try {
      const parsed = JSON.parse(possibleJsonMatch[1])
      console.log('parseJSONResponse: found valid JSON object in string', parsed)
      return typeof parsed === 'object' ? parsed : {}
    } catch (e) {
      // Continue to other parsing attempts
      console.log('parseJSONResponse: couldn\'t parse matched object', e)
    }
  }

  // Try parsing the entire string as JSON
  try {
    const parsed = JSON.parse(jsonString)
    console.log('parseJSONResponse: successfully parsed entire string', parsed)
    return typeof parsed === 'object' ? parsed : {}
  } catch (error) {
    console.error('parseJSONResponse: failed to parse JSON', error)
    console.log('Attempted to parse:', jsonString)
    return {}
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
  const dispatch = useDispatch()

  const { core40SDK, extensionSDK, lookerHostData } = useContext(ExtensionContext)

  const { settings, examples, currentExplore, semanticModels } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  // Only need Vertex AI direct mode settings
  const VERTEX_PROJECT = settings['vertex_project']?.value as string || ''
  const VERTEX_LOCATION = 'us-central1'
  const VERTEX_MODEL = 'gemini-2.0-flash-lite-001'; // Hard-coded model
  
  // Get the OAuth token from settings
  const oauth2Token = settings['oauth2_token']?.value as string || ''

  const currentExploreKey = currentExplore.exploreKey
  const exploreRefinementExamples =
    examples.exploreRefinementExamples[currentExploreKey]

  const modelName = lookerHostData?.extensionId.split('::')[0]

  const callVertexAPI = async (
    contents: string,
    parameters: ModelParameters,
  ) => {
    try {
      console.log('Sending request to Vertex AI with content length:', contents.length);
      
      if (!oauth2Token) {
        throw new Error('OAuth token is required but not provided');
      }

      // Define default parameters
      const defaultParameters = {
        temperature: 0.2,
        maxOutputTokens: 2000,
        topP: 0.8,
        topK: 40
      };
      
      // Override default parameters with any provided
      const mergedParams = { ...defaultParameters, ...parameters };
      
      // Construct the request body according to Vertex AI API specs
      const requestBody = {
        contents: [{
          role: "user",
          parts: [{ text: contents }]
        }],
        generationConfig: {
          temperature: mergedParams.temperature,
          maxOutputTokens: mergedParams.maxOutputTokens,
          topP: mergedParams.topP,
          topK: mergedParams.topK
        }
      };
      
      // Directly call the Vertex AI API using OAuth authentication
      const endpoint = `https://${VERTEX_LOCATION}-aiplatform.googleapis.com/v1/projects/${VERTEX_PROJECT}/locations/${VERTEX_LOCATION}/publishers/google/models/${VERTEX_MODEL}:generateContent`;
      
      console.log(`Making request to: ${endpoint}`);
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${oauth2Token}`
        },
        body: JSON.stringify(requestBody)
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('API call failed:', errorText);
        throw new Error(`API call failed: ${response.status} - ${errorText}`);
      }
      
      const responseData = await response.json();
      console.log('API call successful, response:', responseData);
      
      // Extract text from the response (format similar to the Python code's output)
      if (responseData.candidates && 
          responseData.candidates[0] && 
          responseData.candidates[0].content && 
          responseData.candidates[0].content.parts && 
          responseData.candidates[0].content.parts[0]) {
        return responseData.candidates[0].content.parts[0].text;
      } else {
        throw new Error('Unexpected response format from Vertex AI');
      }
    } catch (error) {
      console.error('Error sending request to Vertex AI:', error);
      throw error;
    }
  }

  const summarizePrompts = useCallback(
    async (promptList: string[]) => {
      const contents = `
    
      Primer
      ----------
      A user is iteractively asking questions to generate an explore URL in Looker. The user is refining his questions by adding more context. The additional prompts he is adding could have conflicting or duplicative information: in those cases, prefer the most recent prompt. 

      Here are some example prompts the user has asked so far and how to summarize them:

${exploreRefinementExamples &&
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
  
  // Helper function for safe JSON parsing
  const safeJsonParse = (jsonString: string | null | undefined, defaultValue: any, fieldName: string) => {
    if (!jsonString) {
      console.warn(`Empty ${fieldName} value`)
      return defaultValue
    }
    
    try {
      return JSON.parse(jsonString)
    } catch (err) {
      console.error(`Error parsing ${fieldName} JSON:`, err)
      console.log('Raw string:', jsonString)
      return defaultValue
    }
  }

  const generateSharedContext = (dimensions: any[], measures: any[], exploreGenerationExamples: any[]) => {
    if (!dimensions.length || !measures.length) {
      showBoundary(new Error('Dimensions or measures are not defined'))
      return
    }
    let exampleText = ''
    if (exploreGenerationExamples && exploreGenerationExamples.length > 0) {
      console.log("Line",exploreGenerationExamples)
      exampleText = exploreGenerationExamples.map((item) => `input: "${item.input}" ; output: ${JSON.stringify(parseLookerURL(item.output))}`).join('\n')
    }
    return `
      # Documentation
      ${looker_simplified_reference}
             
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
          
      # End Documentation
      
           
      # Metadata
      This information is particular to the current Looker instance and data model. The fields below can be used in the response.
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
      # End LookML Metadata
    
      # Example 
        Examples Below include the fields, filters and sometimes visualization configs. 
        They were taken at a different date. ALL DATE RANGES ARE WRONG COMPARING TO CURRENT DATE.
        (BE CAREFUL WITH DATES, DO NOT OUTPUT THE Examples 1:1,  as changes could happen with timeframes and date ranges)
        ${exampleText}
      # End Examples
      
  `}

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
          limit: exploreParams.limit || '3000',
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
      if (!qq) continue; // Skip empty segments
      
      const [key, value] = qq.split('=');
      if (!key || !value) continue; // Skip malformed pairs
      
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
          try {
            const decodedValue = decodeURIComponent(value);
            lookerEncoding[key] = JSON.parse(decodedValue);
          } catch (error) {
            console.error(`Error parsing visualization config: ${error}: ${value}`);
            lookerEncoding[key] = {}; // Use empty object as fallback
          }
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

  const generateFilterParams = useCallback(
    async (prompt: string, sharedContext: string, dimensions: any[], measures: any[]) => {
      // get the filters
      const filterContents = `
      ${sharedContext}
      
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

      // Ensure filterResponseCheckJSON is an array
      const filterResponseArray = Array.isArray(filterResponseCheckJSON) ? filterResponseCheckJSON : []

      // Iterate through each filter
      const filterResponseJSON: any = {}

      // Validate each filter
      filterResponseArray.forEach(function (filter: {
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
    async (prompt: string, sharedContext) => {
      const currentDateTime = new Date().toISOString();

      const contents = `
      ${sharedContext}
      
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
        
      User Request
      ----------
      ${prompt}
      
      `;

      const parameters = {
        max_output_tokens: 6000,
      };

      try {
        const response = await sendMessage(contents, parameters);
        console.log('Raw response from Vertex AI:', response);

        // Attempt to parse the response as JSON
        let responseJSON = parseJSONResponse(response);

        // Fallback: If responseJSON is empty but we have a response string, try direct extraction
        if (Object.keys(responseJSON).length === 0 && response) {
          console.log('Attempting fallback JSON extraction');
          const jsonMatches = response.match(/(\{[\s\S]*?\})/g);
          if (jsonMatches) {
            for (const match of jsonMatches) {
              try {
                const possibleJSON = JSON.parse(match);
                if (typeof possibleJSON === 'object' && possibleJSON !== null) {
                  console.log('Found valid explore params using fallback', possibleJSON);
                  return possibleJSON;
                }
              } catch (e) {
                // Continue to next match
              }
            }
          }
        }

        return responseJSON;
      } catch (error) {
        console.error('Error in generateBaseExploreParams:', error);
        return {};
      }
    },
    [currentExplore],
  );

  const generateExploreParams = useCallback(
    async (
      prompt: string,
      dimensions: any[],
      measures: any[],
      exploreKey: string,
    ) => {
      if (!dimensions.length || !measures.length) {
        showBoundary(new Error('Dimensions or measures are not defined'))
        return
      }
      
      // Get examples for this explore key using our getExamplesForExplore helper
      const exploreData = getExamplesForExplore(exploreKey);
      const exploreGenerationExamples = exploreData.examples || [];
      
      const sharedContext = generateSharedContext(dimensions, measures, exploreGenerationExamples) || ''
      const responseJSON = await generateBaseExploreParams(prompt, sharedContext)

      // Directly return the responseJSON as the final response
      return responseJSON
    },
    [currentExplore, getExamplesForExplore],
  )

  const sendMessage = async (message: string, parameters: ModelParameters) => {
    const wrappedMessage = promptWrapper(message)
    try {
      // Simplified: we only use direct Vertex AI now
      if (!oauth2Token || !VERTEX_PROJECT) {
        throw new Error('OAuth token and Vertex project ID are required');
      }

      const response = await callVertexAPI(wrappedMessage, parameters);
      return typeof response === 'string' ? response : JSON.stringify(response);
    } catch (error) {
      showBoundary(error)
      return ''
    }
  }

  const testVertexSettings = async () => {
    // Simplified: only need to check direct Vertex AI settings
    if (!oauth2Token) {
      console.error('OAuth token is required');
      return false;
    }
    
    if (!VERTEX_PROJECT) {
      console.error('Vertex AI Project ID is required');
      return false;
    }
    
    console.log('Testing Vertex AI with:');
    console.log(`- Project: ${VERTEX_PROJECT}`);
    console.log(`- Location: ${VERTEX_LOCATION || 'us-central1 (default)'}`);
    console.log(`- Model: ${VERTEX_MODEL || 'gemini-1.5-flash (default)'}`);
    
    console.log('Testing Vertex settings with minimal payload...');
    try {
      const testBody = 'test'; // Minimal test payload
      const response = await callVertexAPI(testBody, {});
      
      console.log('Test response received:', Boolean(response));
      
      if (response !== '') {
        dispatch(setVertexTestSuccessful(true));
        return true;
      } else {
        console.error('Empty response from test');
        dispatch(setVertexTestSuccessful(false));
        return false;
      }
    } catch (error) {
      console.error('Error testing Vertex settings:', error);
      dispatch(setVertexTestSuccessful(false));
      return false;
    }
  }

  // New function to get examples for a specific explore directly from raw explore entries
  const getExamplesForExplore = useCallback(
    (exploreKey: string) => {
      const entries = examples.exploreEntries || [];
      
      // Filter the raw entries to get examples for the specific explore
      const filteredExamples = entries
        .filter(entry => entry['golden_queries.explore_id'] === exploreKey)
        .map(entry => ({
          input: entry['golden_queries.input'],
          output: entry['golden_queries.output']
        }))
        .filter(ex => ex.input && ex.output);
      
      // Get refinement examples from the first matching entry
      const refinementEntry = entries.find(entry => 
        entry['golden_queries.explore_id'] === exploreKey && 
        entry['explore_assistant_refinement_examples.examples']
      );
      
      const refinementExamples = refinementEntry ? 
        safeJsonParse(refinementEntry['explore_assistant_refinement_examples.examples'], [], 'refinement_examples') : 
        [];
      
      // Similarly get samples
      const samplesEntry = entries.find(entry => 
        entry['golden_queries.explore_id'] === exploreKey && 
        entry['explore_assistant_samples.samples']
      );
      
      const samples = samplesEntry ? 
        safeJsonParse(samplesEntry['explore_assistant_samples.samples'], [], 'samples') : 
        [];
      
      return {
        examples: filteredExamples,
        refinementExamples,
        samples
      };
    },
    [examples.exploreEntries]
  );

  // New function to determine the best explore for a given prompt
  const determineExplore = async (prompt: string) => {
    try {
      console.log('Determining best explore for prompt:', prompt);
      
      // Get unique explore_ids from the raw entries
      const uniqueExploreIds = [...new Set(
        (examples.exploreEntries || [])
          .map(entry => entry['golden_queries.explore_id'])
          .filter(Boolean)
      )];
      
      const availableExplores = uniqueExploreIds;
      
      if (!availableExplores.length) {
        console.error('No available explores found');
        return null;
      }
      
      // Build context for the LLM with examples and semantic models
      const exploreContext = availableExplores.map(exploreKey => {
        const [modelName, exploreId] = exploreKey.split(':');
        
        // Get examples for this explore using our new function
        const exploreData = getExamplesForExplore(exploreKey);
        const exploreExamples = exploreData.examples || [];
        
        const exploreDimensions = semanticModels[exploreKey]?.dimensions || [];
        const exploreMeasures = semanticModels[exploreKey]?.measures || [];
        
        // Format examples
        const formattedExamples = exploreExamples.slice(0, 3).map(ex => 
          `"${ex.input}"`
        ).join(', ');
        
        // Format a sample of field names
        const fieldSample = [
          ...exploreDimensions.slice(0, 5).map(d => d.name),
          ...exploreMeasures.slice(0, 5).map(m => m.name)
        ].join(', ');
        
        return `Explore: ${exploreKey}
Model: ${modelName}
View: ${exploreId}
Example queries: ${formattedExamples}
Sample fields: ${fieldSample}`;
      }).join('\n\n');
      
      // Create prompt for VertexAI
      const contents = `
# Task
Determine the most appropriate Looker explore to use for the following user question.

# User Question
${prompt}

# Available Explores
${exploreContext}

# Instructions
1. Analyze the user question and determine which explore would be best suited to answer it
2. Look for similarity between the user question and the example queries for each explore
3. Check if the sample fields for each explore match concepts in the user question
4. Return only the explore key (in the format "model:view") of the best match, with no additional text
`;

      // Call VertexAI to determine the best explore
      const response = await sendMessage(contents, {
        temperature: 0.1, // Low temperature for more deterministic output
        max_output_tokens: 100 // Short response needed
      });
      
      // Try to extract a clean explore key from the response
      const cleanResponse = response.trim();
      
      // Check if response is directly one of the available explores
      if (availableExplores.includes(cleanResponse)) {
        console.log(`Explore directly matched: ${cleanResponse}`);
        return cleanResponse;
      }
      
      // Look for an explore key in the response
      for (const exploreKey of availableExplores) {
        if (cleanResponse.includes(exploreKey)) {
          console.log(`Explore found in response: ${exploreKey}`);
          return exploreKey;
        }
      }
      
      // If no direct match, try to interpret as model:view format
      if (cleanResponse.includes(':')) {
        console.log(`Possible explore key format found: ${cleanResponse}`);
        // Check if this explore key exists
        if (availableExplores.includes(cleanResponse)) {
          return cleanResponse;
        }
      }
      
      console.log('No matching explore found, using first available:', availableExplores[0]);
      return availableExplores[0]; // Default to first explore if no match
    } catch (error) {
      console.error('Error determining explore:', error);
      return null;
    }
  };

  return {
    generateExploreParams,
    generateBaseExploreParams,
    generateFilterParams,
    generateVisualizationParams,
    sendMessage,
    summarizePrompts,
    isSummarizationPrompt,
    summarizeExplore,
    testVertexSettings,
    determineExplore,
  }
}

export default useSendVertexMessage
