export interface ExploreQuery {
  fields: string[]
  filters: Record<string, string>
  sorts: string[]
  limit: string
}

export class ExploreHelper {
  static generateExploreUrlFromJSON = (exploreData: ExploreQuery): string => {
    const { fields, filters, sorts, limit } = exploreData

    const fieldsString = fields.map(encodeURIComponent).join(',')
    const filtersString = Object.entries(filters)
      .map(([key, value]) => `f[${encodeURIComponent(key)}]=${value}`)
      .join('&')
    const sortsString = sorts.map(encodeURIComponent).join(',')
    const limitString = `limit=${encodeURIComponent(limit.toString())}`

    const url = `fields=${fieldsString}&${filtersString}&sorts=${sortsString}&${limitString}&toggle=pik,vis`

    return url
  }
}
