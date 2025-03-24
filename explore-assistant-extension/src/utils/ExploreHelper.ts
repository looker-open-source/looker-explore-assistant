import { ExploreParams } from '../slices/assistantSlice'

export class ExploreHelper {

  static exploreQueryArgumentString = (exploreParams: ExploreParams): string => {
    const encodedParams = ExploreHelper.encodeExploreParams(exploreParams)
    return new URLSearchParams(encodedParams).toString()
  }

  static encodeExploreParams = (
    exploreParams: ExploreParams ,
  ): { [key: string]: string } => {
    if (!exploreParams || Object.keys(exploreParams).length === 0) {
      return {}
    }

    const { fields, filters, sorts, limit, pivots, vis_config } = exploreParams

    const fieldsString = fields?.join(',') || ''

    const sortsString = Array.isArray(sorts)
      ? sorts.map((sort) => sort).join(',')
      : ''

    const limitString = limit ? limit.toString() : ''

    const pivotsString = pivots?.join(',') || ''
    const visString = vis_config ? JSON.stringify(vis_config) : ''

    const encodedParams: { [key: string]: string } = {
      fields: fieldsString,
      sorts: sortsString,
      limit: limitString,
      pivots: pivotsString,
      vis: visString,
    }

    if (filters) {
      Object.entries(filters).forEach(([key, value]) => {
        encodedParams[`f[${key}]`] = value
      })
    }

    return encodedParams
  }
}
