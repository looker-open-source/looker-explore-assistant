const GOOGLE_API_KEY = process.env.GOOGLE_API_KEY

export interface EmbedTextResponse {
  embedding: { value: number[] }
}

export interface GenerateTextResponse {
  candidates: Array<{ output: string }>
}

const handleResponse = async (response: Response, method: string) => {
  if (response.status > 299) {
    return `There was an error calling ${method}: ${response.status} - ${response.statusText}`
  }

  console.log("Response: ", response)

  return JSON.parse(await response.text())
}

export const embedText = async (text: string) => {
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta2/models/embedding-gecko-001:embedText?key=${GOOGLE_API_KEY}`,
    {
      method: 'post',
      body: JSON.stringify({ text }),
      headers: { 'Content-Type': 'application/json' },
    }
  )
  const result: EmbedTextResponse = await handleResponse(response, 'embedText')
  return result
}

export const generateText = async (
  question: string,
  temperature = 0.5,
  candidate_count = 1
) => {
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generateText?key=${GOOGLE_API_KEY}`,
    {
      method: 'post',
      body: JSON.stringify({
        prompt: {
          text: question,
        },
        temperature,
        candidate_count,
        safety_settings: [
          { category: 'HARM_CATEGORY_UNSPECIFIED', threshold: 'BLOCK_NONE' },
          {
            category: 'HARM_CATEGORY_DEROGATORY',
            threshold: 'BLOCK_ONLY_HIGH',
          },
          {
            category: 'HARM_CATEGORY_TOXICITY',
            threshold: 'BLOCK_ONLY_HIGH',
          },
          {
            category: 'HARM_CATEGORY_VIOLENCE',
            threshold: 'BLOCK_ONLY_HIGH',
          },
          { category: 'HARM_CATEGORY_SEXUAL', threshold: 'BLOCK_ONLY_HIGH' },
          { category: 'HARM_CATEGORY_MEDICAL', threshold: 'BLOCK_NONE' },
          {
            category: 'HARM_CATEGORY_DANGEROUS',
            threshold: 'BLOCK_MEDIUM_AND_ABOVE',
          },
        ],
      }),
      headers: { 'Content-Type': 'application/json' },
    }
  )
  const result: GenerateTextResponse = await handleResponse(
    response,
    'generateText'
  )
  return result
}

export const generateExploreUrlText = async (
  question: string,
  temperature = 0.5,
  maxOutputTokens = 100,
  topP = 0.8,
  topK = 40,
  candidate_count = 1
) => {
  const response = await fetch(
    `https://generativelanguage.googleapis.com/v1beta2/models/text-bison-001:generateText?key=${GOOGLE_API_KEY}`,
    {
      method: 'post',
      body: JSON.stringify({
        prompt: {
          text: question,
        },
        temperature,
        candidate_count,
        maxOutputTokens,
        topP,
        topK,
        safetySettings: [
          { category: 'HARM_CATEGORY_UNSPECIFIED', threshold: 'BLOCK_NONE' },
          {
            category: 'HARM_CATEGORY_DEROGATORY',
            threshold: 'BLOCK_ONLY_HIGH',
          },
          {
            category: 'HARM_CATEGORY_TOXICITY',
            threshold: 'BLOCK_ONLY_HIGH',
          },
          {
            category: 'HARM_CATEGORY_VIOLENCE',
            threshold: 'BLOCK_ONLY_HIGH',
          },
          { category: 'HARM_CATEGORY_SEXUAL', threshold: 'BLOCK_ONLY_HIGH' },
          { category: 'HARM_CATEGORY_MEDICAL', threshold: 'BLOCK_NONE' },
          {
            category: 'HARM_CATEGORY_DANGEROUS',
            threshold: 'BLOCK_MEDIUM_AND_ABOVE',
          },
        ],
      }),
      headers: { 'Content-Type': 'application/json' },
    }
  )
  const result: GenerateTextResponse = await handleResponse(
    response,
    'generateText'
  )
  return result
}
