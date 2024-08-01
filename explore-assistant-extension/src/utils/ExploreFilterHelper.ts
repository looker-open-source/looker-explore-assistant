export type FieldType = 'string' | 'number' | 'date' | 'boolean'

export interface Field {
  name: string
  type: FieldType
}

export interface FilterExpression {
  [key: string]: string[]
}

export class ExploreFilterValidator {
    static isValidStringFilter(filter: string): boolean {
        const rules: ((f: string) => boolean)[] = [
          (f) => /^[^%,]+$/.test(f), // Exact match
          (f) => /^[^%,]+(,[^%,]+)+$/.test(f), // Multiple exact matches
          (f) => /^%[^%]+%$/.test(f), // Contains
          (f) => /^[^%]+%$/.test(f), // Starts with
          (f) => /^%[^%]+$/.test(f), // Ends with
          (f) => /^[^%]+%[^%]+$/.test(f), // Starts with and ends with
          (f) => f === 'EMPTY' || f === 'NULL', // EMPTY or NULL
          (f) => /^-[^%,]+$/.test(f), // Not equal to
          (f) => /^-(%[^%]+%|[^%]+%|%[^%]+)$/.test(f), // Not contains, not starts with, not ends with
          (f) => f === '-EMPTY' || f === '-NULL', // Not EMPTY or not NULL
          (f) => /^[^%]+%(,[^%,]+)+$/.test(f), // Starts with or exact match
          (f) => /^_[^%]+$/.test(f), // Single character wildcard
        ];
    
        return rules.some((rule) => rule(filter));
      }

  static isValidNumberFilter(filter: string): boolean {
    const singleRules: ((f: string) => boolean)[] = [
      (f) => /^-?\d+(\.\d+)?$/.test(f), // Exact number (including negative)
      (f) => /^NOT\s+-?\d+(\.\d+)?$/.test(f), // NOT number
      (f) => /^(<>|!=|[<>]=?)-?\d+(\.\d+)?$/.test(f), // Relational operators
      (f) => /^(-?\d+(\.\d+)?(,\s*-?\d+(\.\d+)?)+)$/.test(f), // List of numbers
      (f) => /^NOT\s+(-?\d+(\.\d+)?(,\s*-?\d+(\.\d+)?)+)$/.test(f), // NOT list of numbers
      (f) => /^-?\d+(\.\d+)?\s+to\s+-?\d+(\.\d+)?$/.test(f), // Range
      (f) => /^to\s+-?\d+(\.\d+)?$/.test(f), // "to X" (X or less)
      (f) => /^-?\d+(\.\d+)?\s+to$/.test(f), // "X to" (X or greater)
      (f) => /^NULL$/.test(f), // NULL
      (f) => /^NOT\s+NULL$/.test(f), // NOT NULL
      (f) => /^[\[(]-?\d+(\.\d+)?,\s*-?\d+(\.\d+)?[\])]$/.test(f), // Single interval notation
      (f) => /^NOT\s+[\[(]-?\d+(\.\d+)?,\s*-?\d+(\.\d+)?[\])]$/.test(f), // NOT single interval
      (f) => /^[\[(](-inf|-?\d+(\.\d+)?),\s*(inf|-?\d+(\.\d+)?)[\])]$/.test(f), // Interval with infinity
      (f) =>
        /^([\[(]-?\d+(\.\d+)?,\s*-?\d+(\.\d+)?[\])])(,\s*([\[(]-?\d+(\.\d+)?,\s*-?\d+(\.\d+)?[\])])+)$/.test(
          f,
        ), // Multiple intervals
      (f) =>
        /^([\[(]-?\d+(\.\d+)?,\s*-?\d+(\.\d+)?[\])])\s*,\s*-?\d+(\.\d+)?$/.test(
          f,
        ), // Interval and exact number
      (f) =>
        /^-?\d+(\.\d+)?\s*,\s*[\[(]-?\d+(\.\d+)?,\s*-?\d+(\.\d+)?[\])]$/.test(
          f,
        ), // Exact number and interval
      (f) => /^NOT\s+(-?\d+(\.\d+)?\s+to\s+-?\d+(\.\d+)?)$/.test(f), // NOT range
      (f) => /^((-?\d+(\.\d+)?|NOT\s+-?\d+(\.\d+)?)(,\s*|$))+$/.test(f), // Combination of exact and NOT
    ]

    const complexRules: ((f: string) => boolean)[] = [
      (f) => /^(>=|>)-?\d+(\.\d+)?\s+AND\s+(<=|<)-?\d+(\.\d+)?$/.test(f), // AND range
      (f) => /^(<|<=)-?\d+(\.\d+)?\s+OR\s+(>|>=)-?\d+(\.\d+)?$/.test(f), // OR range
    ]

    const parts = filter.split(/\s+OR\s+/)
    return parts.every(
      (part) =>
        singleRules.some((rule) => rule(part)) ||
        complexRules.some((rule) => rule(part)),
    )
  }

  static isValidDateFilter(filter: string): boolean {
    const rules: ((f: string) => boolean)[] = [
      (f) => /^(this|next|last)\s+(week|month|quarter|year)$/.test(f),
      (f) =>
        /^\d+\s+(second|minute|hour|day|week|month|year)s?(\s+ago)?$/.test(f),
      (f) =>
        /^\d+\s+(second|minute|hour|day|week|month|year)s?\s+ago\s+for\s+\d+\s+(second|minute|hour|day|week|month|year)s?$/.test(
          f,
        ),
      (f) =>
        /^before\s+\d+\s+(second|minute|hour|day|week|month|year)s?\s+ago$/.test(
          f,
        ),
      (f) =>
        /^(before|after)\s+\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}:\d{2})?$/.test(f),
      (f) =>
        /^\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}:\d{2})?\s+to\s+\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}:\d{2})?$/.test(
          f,
        ),
      (f) => /^(today|yesterday|tomorrow)$/.test(f),
      (f) =>
        /^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$/i.test(f),
      (f) => /^next\s+(week|month|quarter|year)$/.test(f),
      (f) =>
        /^\d+\s+(second|minute|hour|day|week|month|year)s?\s+from\s+now$/.test(
          f,
        ),
      (f) =>
        /^\d+\s+(second|minute|hour|day|week|month|year)s?\s+from\s+now\s+for\s+\d+\s+(second|minute|hour|day|week|month|year)s?$/.test(
          f,
        ),
      (f) => /^this\s+year\s+to\s+(second|minute|hour|day|week|month)$/.test(f),
      (f) =>
        /^\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}:\d{2})?\s+for\s+\d+\s+(second|minute|hour|day|week|month|year)s?$/.test(
          f,
        ),
    ]

    const parts = filter.split(/\s*,\s*/)
    return parts.every((part) => rules.some((rule) => rule(part)))
  }

  static isValidBooleanFilter(filter: string): boolean {
    return /^(yes|no|true|false)$/i.test(filter)
  }

  static isFilterValid(fieldType: FieldType, filter: string): boolean {
    switch (fieldType) {
      case 'string':
        return this.isValidStringFilter(filter)
      case 'number':
        return this.isValidNumberFilter(filter)
      case 'date':
        return this.isValidDateFilter(filter)
      case 'boolean':
        return this.isValidBooleanFilter(filter)
      default:
        return false
    }
  }

  static validateFilters(
    fields: Field[],
    filterExpression: FilterExpression,
  ): boolean {
    const fieldMap = new Map(fields.map((field) => [field.name, field.type]))

    for (const [filterField, filterValues] of Object.entries(
      filterExpression,
    )) {
      if (!fieldMap.has(filterField)) {
        return false // Field does not exist in the field list
      }

      const fieldType = fieldMap.get(filterField)

      for (const filter of filterValues) {
        if (!this.isFilterValid(fieldType!, filter)) {
          return false // Invalid filter expression
        }
      }
    }

    return true // All checks passed
  }
}
