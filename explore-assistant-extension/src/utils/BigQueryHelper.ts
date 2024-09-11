import { UtilsHelper } from "./Helper"
import { ModelParameters } from "./VertexHelper"

export class BigQueryHelper {
  static generateSQL = (
    model_id: string,
    prompt: string,
    parameters: ModelParameters,
  ) => {
    const escapedPrompt = UtilsHelper.escapeQueryAll(prompt)
    const subselect = `SELECT '` + escapedPrompt + `' AS prompt`

    const {
      max_output_tokens = 1024,
      temperature = 0.05,
      top_p = 0.98,
      flatten_json_output = true,
      top_k = 1,
    } = parameters

    return `
      SELECT ml_generate_text_llm_result AS generated_content
      FROM
      ML.GENERATE_TEXT(
          MODEL \`${model_id}\`,
          (
            ${subselect}
          ),
          STRUCT(
          ${temperature} AS temperature,
          ${max_output_tokens} AS max_output_tokens,
          ${top_p} AS top_p,
          ${flatten_json_output} AS flatten_json_output,
          ${top_k} AS top_k)
        )
    `
  }
}
