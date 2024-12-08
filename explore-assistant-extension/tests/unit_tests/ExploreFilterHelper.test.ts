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
      // This {interval}
      { input: 'this year', expected: true, description: 'This year' },
      { input: 'this month', expected: true, description: 'This month' },
      { input: 'this week', expected: true, description: 'This week' },
      { input: 'this quarter', expected: true, description: 'This quarter' },
      { input: 'this day', expected: false, description: 'Invalid interval' },
    
      // Next {interval}
      { input: 'next year', expected: true, description: 'Next year' },
      { input: 'next month', expected: true, description: 'Next month' },
      { input: 'next week', expected: true, description: 'Next week' },
      { input: 'next quarter', expected: true, description: 'Next quarter' },
      { input: 'next day', expected: false, description: 'Invalid interval' },
    
      // Last {interval}
      { input: 'last year', expected: true, description: 'Last year' },
      { input: 'last month', expected: true, description: 'Last month' },
      { input: 'last week', expected: true, description: 'Last week' },
      { input: 'last quarter', expected: true, description: 'Last quarter' },
      { input: 'last day', expected: false, description: 'Invalid interval' },
    
      // {n} {interval}, {n} {interval} ago
      { input: '3 days', expected: true, description: 'N days' },
      { input: '3 days ago', expected: true, description: 'N days ago' },
      { input: '5 months', expected: true, description: 'N months' },
      { input: '5 months ago', expected: true, description: 'N months ago' },
      { input: '10 years', expected: true, description: 'N years' },
      { input: '10 years ago', expected: true, description: 'N years ago' },
    
      // {n} {interval} ago for {n} {interval}
      {
        input: '3 months ago for 2 days',
        expected: true,
        description: 'N months ago for N days',
      },
      {
        input: '2 years ago for 1 month',
        expected: true,
        description: 'N years ago for N months',
      },
      {
        input: '1 week ago for 3 hours',
        expected: true,
        description: 'N weeks ago for N hours',
      },
      {
        input: '3 days ago for 2 seconds',
        expected: true,
        description: 'N days ago for N seconds',
      },
    
      // Before {n} {interval} ago
      {
        input: 'before 3 days ago',
        expected: true,
        description: 'Before N days ago',
      },
      {
        input: 'before 5 months ago',
        expected: true,
        description: 'Before N months ago',
      },
      {
        input: 'before 1 year ago',
        expected: true,
        description: 'Before N years ago',
      },
    
      // Before {time}, after {time}
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
        input: 'before 2018-01-01',
        expected: true,
        description: 'Before specific date',
      },
      {
        input: 'after 2018-10-05 14:30:00',
        expected: true,
        description: 'After specific datetime',
      },
    
      // {time} to {time}
      {
        input: '2018-05-18 12:00:00 to 2018-05-18 14:00:00',
        expected: true,
        description: 'Datetime range',
      },
      {
        input: '2020-01-01 to 2020-12-31',
        expected: true,
        description: 'Date range',
      },
      {
        input: '2021-06-01 09:00:00 to 2021-06-01 18:00:00',
        expected: true,
        description: 'Datetime range within a day',
      },
      {
        input: '2022-03-15 to 2022-03-16',
        expected: true,
        description: 'Date range over two days',
      },
    
      // This {interval} to {interval}
      {
        input: 'this year to second',
        expected: true,
        description: 'This year to second',
      },
      {
        input: 'this month to day',
        expected: true,
        description: 'This month to day',
      },
      {
        input: 'this week to hour',
        expected: true,
        description: 'This week to hour',
      },
    
      // {time} for {n} {interval}
      {
        input: '2018-01-01 12:00:00 for 3 days',
        expected: true,
        description: 'Specific datetime for N days',
      },
      {
        input: '2020-05-10 for 1 month',
        expected: true,
        description: 'Specific date for N months',
      },
      {
        input: '2019-12-31 for 2 years',
        expected: true,
        description: 'Specific date for N years',
      },
    
      // Today, yesterday, tomorrow
      { input: 'today', expected: true, description: 'Today' },
      { input: 'yesterday', expected: true, description: 'Yesterday' },
      { input: 'tomorrow', expected: true, description: 'Tomorrow' },
    
      // Day of week
      { input: 'Monday', expected: true, description: 'Day of week' },
      { input: 'Tuesday', expected: true, description: 'Day of week' },
      { input: 'Wednesday', expected: true, description: 'Day of week' },
      { input: 'Thursday', expected: true, description: 'Day of week' },
      { input: 'Friday', expected: true, description: 'Day of week' },
      { input: 'Saturday', expected: true, description: 'Day of week' },
      { input: 'Sunday', expected: true, description: 'Day of week' },
    
      // Next {week, month, quarter, fiscal quarter, year, fiscal year}
      { input: 'next week', expected: true, description: 'Next week' },
      { input: 'next month', expected: true, description: 'Next month' },
      { input: 'next quarter', expected: true, description: 'Next quarter' },
      { input: 'next fiscal quarter', expected: true, description: 'Next fiscal quarter' },
      { input: 'next year', expected: true, description: 'Next year' },
      { input: 'next fiscal year', expected: true, description: 'Next fiscal year' },
    
      // {n} {interval} from now
      {
        input: '3 days from now',
        expected: true,
        description: 'N days from now',
      },
      {
        input: '5 months from now',
        expected: true,
        description: 'N months from now',
      },
      {
        input: '10 years from now',
        expected: true,
        description: 'N years from now',
      },
    
      // {n} {interval} from now for {n} {interval}
      {
        input: '3 days from now for 2 weeks',
        expected: true,
        description: 'N days from now for N weeks',
      },
      {
        input: '1 month from now for 3 days',
        expected: true,
        description: 'N months from now for N days',
      },
      {
        input: '1 year from now for 2 months',
        expected: true,
        description: 'N years from now for N months',
      },
    
      // FY{year}, FY{year}-Q{quarter}
      { input: 'FY2018', expected: true, description: 'Fiscal year' },
      { input: 'FY2019-Q1', expected: true, description: 'Fiscal quarter' },
      { input: 'FY2020-Q4', expected: true, description: 'Fiscal quarter' },
      { input: 'FY2021', expected: true, description: 'Fiscal year' },
    
      // Absolute dates
      { input: '2018/05/29', expected: true, description: 'Specific date' },
      { input: '2018/05', expected: true, description: 'Specific month' },
      { input: '2018', expected: true, description: 'Specific year' },
    
      // Invalid inputs
      { input: 'INVALID', expected: false, description: 'Invalid input' },
      { input: '3 days before now', expected: false, description: 'Invalid input' },
      { input: '2018/13', expected: false, description: 'Invalid month' },
      { input: '2018-05-32', expected: false, description: 'Invalid date' },
      { input: 'next decade', expected: false, description: 'Invalid interval' },
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
