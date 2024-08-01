import {
  ExploreFilterValidator,
  Field,
  FilterExpression,
} from '../../src/utils/ExploreFilterHelper'

describe('ExploreFilterValidator', () => {
  describe('String Filters', () => {
    const testCases = [
      { input: 'FOO', expected: true, description: 'Exact match' },
      {
        input: 'FOO,BAR',
        expected: true,
        description: 'Multiple exact matches',
      },
      { input: '%FOO%', expected: true, description: 'Contains' },
      { input: 'FOO%', expected: true, description: 'Starts with' },
      { input: '%FOO', expected: true, description: 'Ends with' },
      {
        input: 'F%OD',
        expected: true,
        description: 'Starts with and ends with',
      },
      { input: 'EMPTY', expected: true, description: 'EMPTY' },
      { input: 'NULL', expected: true, description: 'NULL' },
      { input: '-FOO', expected: true, description: 'Not equal to' },
      {
        input: '-FOO,-BAR',
        expected: true,
        description: 'Multiple not equal to',
      },
      { input: '-%FOO%', expected: true, description: 'Not contains' },
      { input: '-FOO%', expected: true, description: 'Not starts with' },
      { input: '-%FOO', expected: true, description: 'Not ends with' },
      { input: '-EMPTY', expected: true, description: 'Not EMPTY' },
      { input: '-NULL', expected: true, description: 'Not NULL' },
      {
        input: 'FOO%,BAR',
        expected: true,
        description: 'Starts with or exact match',
      },
      {
        input: 'FOO%,-FOOD',
        expected: true,
        description: 'Starts with and not equal to',
      },
      {
        input: '_UF',
        expected: true,
        description: 'Single character wildcard',
      },
    ]

    testCases.forEach(({ input, expected, description }) => {
      it(`isValidStringFilter: ${description} - ${input}`, () => {
        expect(ExploreFilterValidator.isValidStringFilter(input)).toBe(expected)
      })
    })
  })

  describe('Number Filters', () => {
    const testCases = [
      { input: '5', expected: true, description: 'Exact number' },
      { input: 'NOT 5', expected: true, description: 'NOT number' },
      { input: '<>5', expected: true, description: 'Not equal to' },
      {
        input: '!=5',
        expected: true,
        description: 'Not equal to (alternative)',
      },
      { input: '1, 3, 5, 7', expected: true, description: 'List of numbers' },
      {
        input: 'NOT 66, 99, 4',
        expected: true,
        description: 'NOT list of numbers',
      },
      { input: '>1 AND <100', expected: true, description: 'Range with AND' },
      {
        input: '5, NOT 6, NOT 7',
        expected: true,
        description: 'Combination of exact and NOT',
      },
      { input: '5.5 to 10', expected: true, description: 'Range with to' },
      {
        input: '>=5.5 AND <=10',
        expected: true,
        description: 'Range with AND and =',
      },
      { input: 'NOT 3 to 80.44', expected: true, description: 'NOT range' },
      {
        input: '<3 OR >80.44',
        expected: true,
        description: 'Less than OR greater than',
      },
      { input: '1 to', expected: true, description: '1 or greater' },
      { input: '>=1', expected: true, description: 'Greater than or equal to' },
      { input: 'to 10', expected: true, description: '10 or less' },
      { input: '<=10', expected: true, description: 'Less than or equal to' },
      {
        input: '>10 AND <=20 OR 90',
        expected: true,
        description: 'Complex condition',
      },
      {
        input: '>=50 AND <=100 OR >=500 AND <=1000',
        expected: true,
        description: 'Multiple ranges',
      },
      { input: 'NULL', expected: true, description: 'NULL' },
      { input: 'NOT NULL', expected: true, description: 'NOT NULL' },
      { input: '(1, 7)', expected: true, description: 'Open interval' },
      { input: '[5, 90]', expected: true, description: 'Closed interval' },
      { input: '(12, 20]', expected: true, description: 'Half-open interval' },
      { input: '[12, 20)', expected: true, description: 'Half-open interval' },
      { input: '(500, inf)', expected: true, description: 'Open upper bound' },
      { input: '(-inf, 10]', expected: true, description: 'Open lower bound' },
      {
        input: '[0, 9],[20, 29]',
        expected: true,
        description: 'Multiple intervals',
      },
      {
        input: '[0, 10], 20',
        expected: true,
        description: 'Interval and exact number',
      },
      {
        input: 'NOT (3, 12)',
        expected: true,
        description: 'NOT open interval',
      },
      { input: 'INVALID', expected: false, description: 'Invalid input' },
    ]

    testCases.forEach(({ input, expected, description }) => {
      it(`isValidNumberFilter: ${description} - ${input}`, () => {
        expect(ExploreFilterValidator.isValidNumberFilter(input)).toBe(expected)
      })
    })
  })

  describe('Date Filters', () => {
    const testCases = [
      { input: 'this year', expected: true, description: 'This year' },
      { input: '3 days', expected: true, description: 'N days' },
      { input: '3 days ago', expected: true, description: 'N days ago' },
      {
        input: '3 months ago for 2 days',
        expected: true,
        description: 'N months ago for N days',
      },
      {
        input: 'before 3 days ago',
        expected: true,
        description: 'Before N days ago',
      },
      {
        input: 'before 2018-01-01 12:00:00',
        expected: true,
        description: 'Before specific datetime',
      },
      {
        input: 'after 2018-10-05',
        expected: true,
        description: 'After specific date',
      },
      {
        input: '2018-05-18 12:00:00 to 2018-05-18 14:00:00',
        expected: true,
        description: 'Datetime range',
      },
      {
        input: 'this year to second',
        expected: true,
        description: 'This year to second',
      },
      {
        input: '2018-01-01 12:00:00 for 3 days',
        expected: true,
        description: 'Specific datetime for N days',
      },
      { input: 'today', expected: true, description: 'Today' },
      { input: 'yesterday', expected: true, description: 'Yesterday' },
      { input: 'tomorrow', expected: true, description: 'Tomorrow' },
      { input: 'Monday', expected: true, description: 'Day of week' },
      { input: 'next week', expected: true, description: 'Next week' },
      {
        input: '3 days from now',
        expected: true,
        description: 'N days from now',
      },
      {
        input: '3 days from now for 2 weeks',
        expected: true,
        description: 'N days from now for N weeks',
      },
      { input: 'INVALID', expected: false, description: 'Invalid input' },
    ]

    testCases.forEach(({ input, expected, description }) => {
      it(`isValidDateFilter: ${description} - ${input}`, () => {
        expect(ExploreFilterValidator.isValidDateFilter(input)).toBe(expected)
      })
    })
  })

  describe('Boolean Filters', () => {
    const testCases = [
      { input: 'yes', expected: true, description: 'yes (lowercase)' },
      { input: 'Yes', expected: true, description: 'Yes (capitalized)' },
      { input: 'no', expected: true, description: 'no (lowercase)' },
      { input: 'No', expected: true, description: 'No (capitalized)' },
      { input: 'TRUE', expected: true, description: 'TRUE (uppercase)' },
      { input: 'FALSE', expected: true, description: 'FALSE (uppercase)' },
      { input: 'true', expected: true, description: 'true (lowercase)' },
      { input: 'false', expected: true, description: 'false (lowercase)' },
      { input: 'INVALID', expected: false, description: 'Invalid input' },
    ]

    testCases.forEach(({ input, expected, description }) => {
      it(`isValidBooleanFilter: ${description} - ${input}`, () => {
        expect(ExploreFilterValidator.isValidBooleanFilter(input)).toBe(
          expected,
        )
      })
    })
  })

  describe('validateFilters', () => {
    const fields: Field[] = [
      { name: 'string_field', type: 'string' },
      { name: 'number_field', type: 'number' },
      { name: 'date_field', type: 'date' },
      { name: 'boolean_field', type: 'boolean' },
    ]

    it('should return true for valid filters', () => {
      const filterExpression: FilterExpression = {
        string_field: ['FOO%', 'BAR'],
        number_field: ['5', '>10 AND <=20'],
        date_field: ['this year', '3 days ago'],
        boolean_field: ['yes'],
      }
      expect(
        ExploreFilterValidator.validateFilters(fields, filterExpression),
      ).toBe(true)
    })

    it('should return false for invalid filters', () => {
      const filterExpression: FilterExpression = {
        string_field: ['INVALID%'],
        number_field: ['5', 'INVALID'],
        date_field: ['this year', 'INVALID'],
        boolean_field: ['INVALID'],
      }
      expect(
        ExploreFilterValidator.validateFilters(fields, filterExpression),
      ).toBe(false)
    })

    it('should return false for non-existing fields', () => {
      const filterExpression: FilterExpression = {
        non_existing_field: ['FOO'],
      }
      expect(
        ExploreFilterValidator.validateFilters(fields, filterExpression),
      ).toBe(false)
    })
  })
})
