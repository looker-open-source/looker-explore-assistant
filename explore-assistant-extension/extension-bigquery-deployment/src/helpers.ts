/*

MIT License

Copyright (c) 2023 Looker Data Sciences, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

interface GenerateText {
    model: string,
    explore: string,
    input: string
}

interface GenerateTextRequest extends GenerateText {
    metadata: string,
    model_id: string
}

interface GenerateTextFeedback extends GenerateText {
    response?: string,
    accurate?: boolean,
    feedback?: string
}

const generateText = (request: GenerateTextRequest) => {
    return `
          DECLARE context STRING;
          SET context = """Youre a developer who would transalate questions to a structured URL query based on the following dictionary - choose only the fileds in the below description
          user_order_facts is an extension of user and should be used when referring to users or customers.Generate only one answer, no more.""";

          SELECT ml_generate_text_llm_result AS generated_content
          FROM ML.GENERATE_TEXT(
              MODEL ${request.model_id},
              (
                  SELECT FORMAT('Context: %s; LookML Metadata: %s; Examples: %s; input: %s, output: ',context,"${request.metadata}",examples.examples, "${request.input}") as prompt
                  FROM explore_assistant.explore_assistant_examples as examples
                  WHERE examples.explore_id = "${request.model}:${request.explore}"
              ),
                  STRUCT(
                      0.1 AS temperature,
                      1024 AS max_output_tokens,
                      0.95 AS top_p,
                      40 AS top_k,
                      TRUE AS flatten_json_output
              )
          )
    `
}

const insertResponse = (request: GenerateTextFeedback) => {
    return `
        INSERT INTO explore_assistant_demo.explore_assistant_responses (explore_id,input,output,accurate,feedback)
        VALUES ('${request.model}:${request.explore}','${request.input}','${request.response}',,)
    `
}

const insertResponseFeedback = (request: GenerateTextFeedback) => {
    return `
        UPDATE explore_assistant_demo.explore_assistant_responses SET accurate = ${request.accurate} AND feedback = '${request.feedback}'
        WHERE explore_id = '${request.model}:${request.explore}'
    `
}

export {generateText, insertResponse, insertResponseFeedback};