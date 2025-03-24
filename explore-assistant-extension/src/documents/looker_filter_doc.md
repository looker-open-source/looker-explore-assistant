# Looker Filter Expressions

Filter expressions are an advanced way to filter Looker queries, and this page describes how to write them. In the Explore section of Looker you can use them by adding a filter and choosing the matches (advanced) option. They are also used in LookML for elements that take a filter parameter.

Please note the type of filter expression you can use depends on the type (ie. string, date and time, boolean, number) of field you are filtering on. Please ensure you are checking the field type when applying filter expressions. 
Filters are not always necessary to get results, do not apply filters if they are not needed.

## String

Matches in string filters depend on the case_sensitive setting in your model file, and on whether your dialect supports case-sensitivity. For example, if case_sensitive is enabled in your model, the expression FOO% will not match the word "food". If case_sensitive isn't enabled, or if your dialect doesn't support case-sensitivity, the expression FOO% will match the word "food".

| Example   | Description   |
|-----------|-------------------------------------------------------------------------------|
| FOO       | is equal to "FOO", exactly |
| FOO,BAR   | is equal to either "FOO" or "BAR", exactly  |
| %FOO%     | contains "FOO", matches "buffoon" and "fast |
| FOO%      | starts with "FOO", matches "foolish" and "food" but not "buffoon" or "fast food"   |
| %FOO      | ends with "FOO", matches "buffoo" and "fast foo" but not "buffoon" or "fast food"   |
| F%OD      | starts with an "F" and ends with "OD", matches "fast food"                                                                                   |
| EMPTY     | string is empty (has zero characters) or is null (no value)  |
| NULL      | value is null (when it is used as part of a LookML filter expression, place NULL in quotes, as shown on the filters documentation page)       |
| -FOO      | is not equal to "FOO" (is any value except "FOO"), matches "pizza", "trash", "fun" but not "foo"  |
| -FOO,-BAR | is not equal to either "FOO" or "BAR", matches any value except "FOO" and "BAR" |
| -%FOO%    | doesn't contain "FOO", does not match "buffoon" or "fast food"      |
| -FOO%     | doesn't start with "FOO", does not match "foolish" or "food"   |
| -%FOO     | doesn't end with "FOO", does not match "buffoo" or "fast foo"       |
| -EMPTY    | string is not empty (has at least one character)  |
| -NULL     | value of column is not null (when it is used as part of a LookML filter expression, place -NULL in quotes, as shown on the filters documentation page) |
| FOO%,BAR  | starts with "FOO" or is "BAR" exactly, matches "food" and matches "bar" but not "barfood"    |
| FOO%,-FOOD| starts with "FOO" but is not "FOOD"  |
| _UF       | has any single character followed by "UF", matches "buffoon"    |

## Date and Time

Looker date filtering allows for English phrases to be used instead of SQL date functions. Use this if the field type starts with date_. It might be date_date, date_time, date_week, date_month, date_quarter, or date_year.

For the following examples:

* {n} is an integer.
* {interval} is a time increment such as hours, days, weeks, or months. The phrasing you use determines whether the {interval} will include partial time periods or only complete time periods. For example, the expression 3 days includes the current, partial day as well as the prior two days. The expression 3 days ago for 3 days includes the previous three complete days and excludes the current, partial day. See the Relative Dates section for more information.
* {time} can specify a time formatted as either YYYY-MM-DD HH:MM:SS or YYYY/MM/DD HH:MM:SS, or a date formatted as either YYYY-MM-DD or YYYY/MM/DD. When using the form YYYY-MM-DD, be sure to include both digits for the month and day, for example, 2016-01. Truncating a month or day to a single digit is interpreted as an offset, not a date. For example, 2016-1 is interpreted as 2016 minus one year, or 2015.

These are all the possible combinations of date filters:

| Combination                                         | Example                                            | Notes                                                        |
|-----------------------------------------------------|----------------------------------------------------|--------------------------------------------------------------|
| this {interval}                                     | this month                                         | You can use this week, this month, this quarter, or this year. Note that this day isn't supported. If you want to get data from the current day, you can use today.    |
| {n} {interval}                                      | 3 days                                             | You can use a number combined with days, weeks, months, quarters or years. This will return the last number of days, weeks, months, quarters or years you specify in the combination. For example the last 6 months or last 30 days. This is a very common filter. |
| {n} {interval} ago                                  | 3 days ago                                         | You can use a number combined with days, weeks, months, quarters or years ago. This will return the day you specify in the combination. 3 days ago will return the date 3 days prior to the current date. For example 3 days ago will not include the days between 3 days ago and today. Do not confuse this with the {n} interval filter.  |
| {n} {interval} ago for {n} {interval}               | 3 months ago for 2 days                            | You can use a number combined with days, weeks, months, quarters or years ago for the duration of a number you and interval you specify. This will return date range you specify in the combination. 3 months ago for 2 days will return the date for a range of 2 days 3 months prior to the current date.    |
| before {n} {interval} ago                           | before 3 days ago                                  | You can use this combination to specify a number combined with days, weeks, months, quarters or years in the desired range before ending the date range. Before 3 days ago will return all dates before 3 days of the current date.    |
| before {time}                                       | before 2018-01-01 12:00:00                         | Before is not inclusive of the time you specify. The expression before 2018-01-01 will return data from all dates before 2018-01-01, but it won't return data from 2018-01-01. |
| after {time}                                        | after 2018-10-05                                   | After is inclusive of the time you specify. So, the expression after 2018-10-05 will return data from 2018-10-05 and all dates later than 2018-10-05.  |
| {time} to {time}                                    | 2018-05-18 12:00:00 to 2018-05-18 14:00:00         | The initial time value is inclusive but the latter time value is not. So the expression 2018-05-18 12:00:00 to 2018-05-18 14:00:00 will return data with the time "2018-05-18 12:00:00" through "2018-05-18 13:59:59". |
| this {interval} to {interval}                       | this year to second                                |    The beginning of each interval is used. For example, the expression this year to second returns data from the beginning of the year the query is run through to the beginning of the second the query is run. this week to day returns data from the beginning of the week the query is run through to the beginning of the day the query is run.   |
| {time} for {n} {interval}                           | 2018-01-01 12:00:00 for 3 days                     | The initial time value is inclusive but the latter number and interval values are not. So the expression 2018-05-18 12:00:00 for 3 days will return data with the time "2018-01-01 12:00:00" through "2018-01-04 12:00:00".    |
| today                                               | today                                              | Returns todays date    |
| yesterday                                           | yesterday                                          | Returns yesterdays date    |
| tomorrow                                            | tomorrow                                           | Returns tomorrows date |
| {day of week}                                       | Monday                                             | Specifying a day of week with a Dimension Group Date field returns the most recent date that matches the specified day of week. For example, the expression Dimension Group Date matches (advanced) Monday returns the most recent Monday. You can also use {day of week} with the before and after keywords in this context. For example, the expression Dimension Group Date matches (advanced) after Monday returns the most recent Monday and everything after the most recent Monday. The expression Dimension Group Date matches (advanced) before Monday returns every day before the most recent Monday, but it doesn't return the most recent Monday. Specifying a day of the week with a Dimension Group Day of Week field returns every day that matches the specified day of week. So the expression Dimension Group Day of Week matches (advanced) Monday returns every Monday.   |
| next {week, month, quarter, fiscal quarter, year, fiscal year} | next week                               | The next keyword is unique in that it requires one of the intervals listed previously and won't work with other intervals. |
| {n} {interval} from now                            | 3 days from now                                     | You can use a number combined with days, weeks, months, quarters or years from now. This will return a future date the number of days, weeks, months, quarters or years you specify in the combination.    |
| {n} {interval} from now for {n} {interval}         | 3 days from now for 2 weeks                         | You can use a number combined with days, weeks, months, quarters or years from now for the duration of a number you and interval you specify. This will return a date range in the future you specify in the combination. 3 days ago for 2 weeks will return the dates for a range of 3 days 2 weeks ahead of the current date.    |


Date filters can also be combined together:
* To get OR logic: Type multiple conditions into the same filter, separated by commas. For example, today, 7 days ago means "today or 7 days ago".
* To get AND logic: Type your conditions, one by one, into multiple date or time filters. For example, you could put after 2014-01-01 into a Created Date filter, then put before 2 days ago into a Created Time filter. This would mean "January 1st, 2014 and after, and before 2 days ago".

### Absolute Dates

Absolute date filters use the specific date values to generate query results. These are useful when creating queries for specific date ranges.

| Example                   | Description                                                                                                                  |
|---------------------------|------------------------------------------------------------------------------------------------------------------------------|
| 2018/05/29                | sometime on 2018/05/29                                                                                                        |
| 2018/05/10 for 3 days     | from 2018/05/10 00:00:00 through 2018/05/12 23:59:59                                                                          |
| after 2018/05/10          | 2018/05/10 00:00:00 and after                                                                                                |
| before 2018/05/10         | before 2018/05/10 00:00:00                                                                                                   |
| 2018/05                   | within the entire month of 2018/05                                                                                           |
| 2018/05 for 2 months      | within the entire months of 2018/05 and 2018/06                                                                              |
| 2018/05/10 05:00 for 5 hours | from 2018/05/10 05:00:00 through 2018/05/10 09:59:59                                                                      |
| 2018/05/10 for 5 months   | from 2018/05/10 00:00:00 through 2018/10/09 23:59:59                                                                         |
| 2018                      | entire year of 2018 (2018/01/01 00:00:00 through 2018/12/31 23:59:59)                                                        |
| FY2018                    | entire fiscal year starting in 2018 (if your Looker developers have specified that your fiscal year starts in April then this is 2018/04/01 00:00 through 2019/03/31 23:59) |
| FY2018-Q1                 | first quarter of the fiscal year starting in 2018 (if your Looker developers have specified that your fiscal year starts in April then this is 2018/04/01 00:00:00 through 2018/06/30 23:59:59) |


### Relative Dates

Relative date filters allow you to create queries with rolling date values relative to the current date. These are useful when creating queries that update each time you run the query.

For all of the following examples, assume today is Friday, 2018/05/18 18:30:02. In Looker, weeks start on Monday unless you change that setting with week_start_day.

Relative date filters allow you to create queries with rolling date values relative to the current date. These are useful when creating queries that update each time you run the query.

For all of the following examples, assume today is Friday, 2018/05/18 18:30:02. In Looker, weeks start on Monday unless you change that setting with `week_start_day`.

#### Seconds
| Example                      | Description                                              |
|------------------------------|----------------------------------------------------------|
| 1 second                     | the current second (2018/05/18 18:30:02)                 |
| 60 seconds                   | 60 seconds ago for 60 seconds (2018/05/18 18:29:02 through 2018/05/18 18:30:01) |
| 60 seconds ago for 1 second  | 60 seconds ago for 1 second (2018/05/18 18:29:02)        |

#### Minutes
| Example                      | Description                                              |
|------------------------------|----------------------------------------------------------|
| 1 minute                     | the current minute (2018/05/18 18:30:00 through 18:30:59) |
| 60 minutes                   | 60 minutes ago for 60 minutes (2018/05/18 17:31:00 through 2018/05/18 18:30:59) |
| 60 minutes ago for 1 minute  | 60 minutes ago for 1 minute (2018/05/18 17:30:00 through 2018/05/18 17:30:59) |

#### Hours
| Example                      | Description                                              |
|------------------------------|----------------------------------------------------------|
| 1 hour                       | the current hour (2018/05/18 18:00 through 2018/05/18 18:59) |
| 24 hours                     | the same hour of day that was 24 hours ago for 24 hours (2018/05/17 19:00 through 2018/05/18 18:59) |
| 24 hours ago for 1 hour      | the same hour of day that was 24 hours ago for 1 hour (2018/05/17 18:00 until 2018/05/17 18:59) |

#### Days
| Example                      | Description                                              |
|------------------------------|----------------------------------------------------------|
| today                        | the current day (2018/05/18 00:00 through 2018/05/18 23:59) |
| 2 days                       | all of yesterday and today (2018/05/17 00:00 through 2018/05/18 23:59) |
| 1 day ago                    | just yesterday (2018/05/17 00:00 until 2018/05/17 23:59)  |
| 7 days ago for 7 days        | the last complete 7 days (2018/05/11 00:00 until 2018/05/17 23:59) |
| today for 7 days             | the current day, starting at midnight, for 7 days into the future (2018/05/18 00:00 until 2018/05/24 23:59) |
| last 3 days                  | 2 days ago through the end of the current day (2018/05/16 00:00 until 2018/05/18 23:59) |
| 7 days from now              | 7 days in the future (2018/05/18 00:00 until 2018/05/25 23:59) |

#### Weeks
| Example                      | Description                                              |
|------------------------------|----------------------------------------------------------|
| 1 week                       | top of the current week going forward (2018/05/14 00:00 through 2018/05/20 23:59) |
| this week                    | top of the current week going forward (2018/05/14 00:00 through 2018/05/20 23:59) |
| before this week             | anytime until the top of this week (before 2018/05/14 00:00) |
| after this week              | anytime after the top of this week (2018/05/14 00:00 and later) |
| next week                    | the following Monday going forward 1 week (2018/05/21 00:00 through 2018/05/27 23:59) |
| 2 weeks                      | a week ago Monday going forward (2018/05/07 00:00 through 2018/05/20 23:59) |
| last week                    | synonym for "1 week ago"                                 |
| 1 week ago                   | a week ago Monday going forward 1 week (2018/05/07 00:00 through 2018/05/13 23:59) |

#### Months
| Example                      | Description                                              |
|------------------------------|----------------------------------------------------------|
| 1 month                      | the current month (2018/05/01 00:00 through 2018/05/31 23:59) |
| this month                   | synonym for "0 months ago" (2018/05/01 00:00 through 2018/05/31 23:59) |
| 2 months                     | the past two months (2018/04/01 00:00 through 2018/05/31 23:59) |
| last month                   | all of 2018/04                                            |
| 2 months ago                 | all of 2018/03                                            |
| before 2 months ago          | all time before 2018/03/01                                |
| next month                   | all of 2018/06                                            |
| 2 months from now            | all of 2018/07                                            |
| 6 months from now for 3 months | 2018/11 through 2019/01                                  |

* note for relative dates, the last 3 days is much more common than 3 days ago. The last 2 years is much more common that 2 years ago. 

#### Years

| Example             | Description                                                                                          |
|---------------------|------------------------------------------------------------------------------------------------------|
| 1 year              | all of the current year (2018/01/01 00:00 through 2018/12/31 23:59)                                  |
| this year           | all of the current year (2018/01/01 00:00 through 2018/12/31 23:59)                                  |
| next year           | all of the following year (2019/01/01 00:00 through 2019/12/31 23:59)                                |
| 2 years             | the past two years (2017/01/01 00:00 through 2018/12/31 23:59)                                       |
| last year           | all of 2017                                                                                          |
| 2 years ago         | all of 2016                                                                                          |
| before 2 years ago  | all time before 2016/01/01 (does not include any days between 2016/01/01 and 2016/05/18)             |

## Boolean

Filtering on true or false type values in Looker requires you to know what type of true or false value you're interacting with. Use this if the field type is a yesno or boolean.

### Examples

| Example      | Description                                                                                                           |
|--------------|-----------------------------------------------------------------------------------------------------------------------|
| yes or Yes   | field evaluates to true                                                                                               |
|              | **Looker developers:** for `type: yesno` dimensions use lowercase, for filters parameters (like those used in a measure or used in an `always_filter`) use uppercase |
| no or No     | field evaluates to false                                                                                              |
|              | **Looker developers:** for `type: yesno` dimensions use lowercase, for filters parameters (like those used in a measure or used in an `always_filter`) use uppercase |
| TRUE         | field contains true (for fields that contain Boolean database values)                                                 |
| FALSE        | field contains false (for fields that contain Boolean database values)                                                |

## Numbers

Filters on numbers support both natural language expressions (for example, `3 to 10`) and relational operators (for example, `>20`). Looker supports the `OR` operator to express multiple filter ranges (for example, `3 to 10 OR 30 to 100`). The `AND` operator can be used to express numeric ranges with relational operators (for example, `>=3 AND <=10`) to specify a range. Filters on numbers can also use algebraic interval notation to filter numeric fields.

**Note:** The syntax for numeric filter expressions using `NOT` may not be intuitive. If the first filter condition contains a `NOT`, and no other filter conditions contain a `NOT`, then all of the filter conditions will be negated. See the following examples for more information.

#### Examples

| Example                      | Description                                                                                              |
|------------------------------|----------------------------------------------------------------------------------------------------------|
| 5                            | is exactly 5                                                                                            |
| NOT 5                        | is any value but exactly 5                                                                               |
| <>5                          | is any value but exactly 5                                                                               |
| !=5                          | is any value but exactly 5                                                                               |
| 1, 3, 5, 7                   | is one of the values 1, 3, 5, or 7, exactly                                                              |
| NOT 66, 99, 4                | is not one of the values 66, 99, or 4, exactly                                                           |
| >1 AND <100, NOT 2           | is greater than 1 and less than 100, is not 2                                                            |
| NOT >1, 2, <100              | is less than or equal to 1, is not 2, and is greater than or equal to 100 (Looker recognizes that this is an impossible condition, and will instead write the SQL `IS NULL`) |
| 5, NOT 6, NOT 7              | is 5, is not 6 or 7                                                                                      |
| 5.5 to 10                    | is 5.5 or greater but also 10 or less                                                                    |
| >=5.5 AND <=10               | is 5.5 or greater but also 10 or less                                                                    |
| NOT 3 to 80.44               | is less than 3 or greater than 80.44                                                                     |
| <3 OR >80.44                 | is less than 3 or greater than 80.44                                                                     |
| 1 to                         | is 1 or greater                                                                                          |
| >=1                          | is 1 or greater                                                                                          |
| to 10                        | is 10 or less                                                                                            |
| <=10                         | is 10 or less                                                                                            |
| >10 AND <=20 OR 90           | is greater than 10 and less than or equal to 20, or is 90 exactly                                        |
| >=50 AND <=100 OR >=500 AND <=1000 | is between 50 and 100, inclusive, or between 500 and 1000, inclusive                                      |
| NULL                         | has no data in it (when it is used as part of a LookML filter expression, place `NULL` in quotes, as shown on the filters documentation page) |
| NOT NULL                     | has some data in it (when it is used as part of a LookML filter expression, place `NOT NULL` in quotes, as shown on the filters documentation page) |
| (1, 7)                       | interpreted as 1 < x < 7 where the endpoints aren't included. While this notation resembles an ordered pair, in this context it refers to the interval upon which you are working. |
| [5, 90]                      | interpreted as 5 <= x <= 90 where the endpoints are included                                             |
| (12, 20]                     | interpreted as 12 < x <= 20 where 12 is not included, but 20 is included                                 |
| [12, 20)                     | interpreted as 12 <= x < 20 where 12 is included, but 20 is not included                                 |
| (500, inf)                   | interpreted as x > 500 where 500 is not included and infinity is always expressed as being "open" (not included). `inf` may be omitted and (500, inf) may be written as (500,) |
| (-inf, 10]                   | interpreted as x <= 10 where 10 is included and infinity is always expressed as being "open" (not included). `inf` may be omitted and (-inf, 10] may be written as (,10] |
| [0,9],[20,29]                | the numbers between 0 and 9 inclusive or 20 to 29 inclusive                                              |
| [0,10],20                    | 0 to 10 inclusive or 20                                                                                  |
| NOT (3,12)                   | interpreted as x < 3 and x > 12
                                                                          |
