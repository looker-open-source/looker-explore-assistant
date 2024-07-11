export interface ExploreQuery {
  fields: string[]
  filters: Record<string, string>
  sorts: string[]
  limit: string
}

export class ExploreHelper {
  static generateExploreUrlFromJSON = (exploreData: ExploreQuery): string => {
    if (!exploreData || typeof exploreData !== 'object') {
      return ''
    }

    const { fields, filters, sorts, limit } = exploreData

    if (!Array.isArray(fields) || fields.length === 0) {
      return ''
    }

    const fieldsString = fields
      .map((field) => encodeURIComponent(field))
      .join(',')

    const filtersString = Object.entries(filters)
      .map(
        ([key, value]) =>
          `f[${encodeURIComponent(key)}]=${value}`,
      )
      .join('&')

    const sortsString = Array.isArray(sorts)
      ? sorts.map((sort) => encodeURIComponent(sort)).join(',')
      : ''

    const limitString = limit
      ? `limit=${encodeURIComponent(limit.toString())}`
      : ''

    const queryParts = [
      fieldsString && `fields=${fieldsString}`,
      filtersString,
      sortsString && `sorts=${sortsString}`,
      limitString,
      'toggle=pik,vis',
    ]
      .filter(Boolean)
      .join('&')

    return queryParts ? queryParts : ''
  }
}
