## Intervals

Interval options
The intervals parameter tells the dimension group which interval units it should use to measure the time difference between the sql_start time and the sql_end time. The intervals parameter is supported only for dimension groups of type: duration.

If intervals is not included, the dimension group will include all possible intervals.

The options for the intervals parameter are:

Interval |  Description | Example Output
|--------|-------------------------------------------------------------|--------------------|
day	     |  Calculates a time difference in days.                      |	9 days
hour	 |  Calculates a time difference in hours.                     |	171 hours
minute	 |  Calculates a time difference in minutes.                   |	10305 minutes
month	 |  Calculates a time difference in months.	                   |    3 months
quarter	 |  Calculates a time difference in quarters of the year.	   |    2 quarters
second	 |  Calculates a time difference in seconds.	               |    606770 seconds
week	 |  Calculates a time difference in weeks.	                   |    6 weeks
year	 |  Calculates a time difference in years.	                   |    2 years

## Timeframes

Timeframe options
The timeframes parameter is supported only for dimension groups of type: time. For dimension groups of type: duration, use the intervals parameter instead.

The timeframes parameter tells the dimension group which dimensions it should produce and includes the following options:

Special timeframes
Time timeframes
Date timeframes
Week timeframes
Month timeframes
Quarter timeframes
Year timeframes
hourX timeframes
minuteX timeframes
millisecondX timeframes

Special timeframes
Timeframe | Description | Example Output
|---------|-------------|-------------------------------------------------------------------|
raw	      | The raw value from your database, without casting or time zone conversion. raw is accessible only within LookML and won't show up on the Explore page. The raw timeframe returns a timestamp, unlike most other timeframes that return a formatted string. It is primarily used for performing date operations on a field. | 2014-09-03 17:15:00 +0000
yesno	  | A yesno dimension, returning "Yes" if the datetime has a value, otherwise "No". Unlike other timeframes, when you refer to a yesno timeframe dimension from another field, don't include the timeframe in the reference. For example, to refer to a yesno timeframe in the dimension_group: created, use the syntax $ {created}, not $ {created_yesno}. | Yes

Time timeframes
Timeframe | Description | Example Output
|---------|-------------|-------------------------------------------------------------------|
time	     | Datetime of the underlying field (some SQL dialects show as much precision as your database contains, while others show only to the second)	| 2014-09-03 17:15:00
time_of_day  | Time of day | 17:15
hour	     | Datetime truncated to the nearest hour | 2014-09-03 17
hour_of_day  | Integer hour of day of the underlying field |	17
hourX	     | Splits each day into intervals with the specified number of hours. |	See Using hourX.
minute	     | Datetime truncated to the nearest minute | 2014-09-03 17:15
minuteX	     | Splits each hour into intervals with the specified number of minutes. | See Using minuteX.
second	     | Datetime truncated to the nearest second	| 2014-09-03 17:15:00
millisecond	 | Datetime truncated to the nearest millisecond (see the Dialect support for milliseconds and microseconds section on this page for information on dialect support). | 2014-09-03 17:15:00.000
millisecondX |	Splits each second into intervals with the specified number of milliseconds (see the Dialect support for milliseconds and microseconds section on this page for information on dialect support). | See Using millisecondX.
microsecond  |	Datetime truncated to the nearest microsecond (see the Dialect support for milliseconds and microseconds section on this page for information on dialect support). | 2014-09-03 17:15:00.000000

Date timeframes
Timeframe | Description | Example Output
|---------|-------------|-------------------------------------------------------------------|
date      | Date of the underlying field | 2017-09-03

Week timeframes
Timeframe | Description | Example Output
|---------|-------------|-------------------------------------------------------------------|
week	          | Date of the week starting on a Monday of the underlying datetime | 2017-09-01
day_of_week	      | Day of week alone | Wednesday
day_of_week_index |	Day of week index (0 = Monday, 6 = Sunday) | 2

Month timeframes
Timeframe | Description | Example Output
|---------|-------------|-------------------------------------------------------------------|
month	         | Year and month of the underlying datetime | 2014-09
month_num	     | Integer number of the month of the underlying datetime | 9
fiscal_month_num |	Integer number of the fiscal month of the underlying datetime | 6
month_name	     | Name of the month | September
day_of_month	 | Day of month | 3
To use the fiscal_month_num timeframes, the fiscal_month_offset parameter must be set in the model.

Quarter timeframes
Timeframe | Description | Example Output
|---------|-------------|-------------------------------------------------------------------|
quarter	               | Year and quarter of the underlying datetime | 2017-Q3
fiscal_quarter         | Fiscal year and quarter of the underlying datetime | 2017-Q3
quarter_of_year	       | Quarter of the year preceded by a "Q" | Q3
fiscal_quarter_of_year | Fiscal quarter of the year preceded by a "Q" | Q3
To use the fiscal_quarter and fiscal_quarter_of_year timeframes, the fiscal_month_offset parameter must be set in the model.

Year timeframes
Timeframe | Description | Example Output
|---------|-------------|-------------------------------------------------------------------|
year	     | Integer year of the underlying datetime | 2017
fiscal_year	 | Integer fiscal year of the underlying datetime | FY2017
day_of_year	 | Day of year | 143
week_of_year |	Week of the year as a number | 17
To use the fiscal_year timeframe, the fiscal_month_offset parameter must be set in the model.


Using hourX
In hourX the X is replaced with 2, 3, 4, 6, 8, or 12.

This will split up each day into intervals with the specified number of hours. For example, hour6 will split each day into 6 hour segments, which will appear as follows:

2014-09-01 00:00:00
2014-09-01 06:00:00
2014-09-01 12:00:00
2014-09-01 18:00:00
To give an example, a row with a time of 2014-09-01 08:03:17 would have a hour6 of 2014-09-01 06:00:00.


Using minuteX
In minuteX the X is replaced with 2, 3, 4, 5, 6, 10, 12, 15, 20, or 30.

This will split up each hour into intervals with the specified number of minutes. For example, minute15 will split each hour into 15 minute segments, which will appear as follows:

2014-09-01 01:00:00
2014-09-01 01:15:00
2014-09-01 01:30:00
2014-09-01 01:45:00
To give an example, a row with a time of 2014-09-01 01:17:35 would have a minute15 of 2014-09-01 01:15:00.


Using millisecondX
In millisecondX the X is replaced with 2, 4, 5, 8, 10, 20, 25, 40, 50, 100, 125, 200, 250, or 500.

This will split up each second into intervals with the specified number of milliseconds. For example, millisecond250 will split each second into 250 millisecond segments, which will appear as follows:

2014-09-01 01:00:00.000
2014-09-01 01:00:00.250
2014-09-01 01:00:00.500
2014-09-01 01:00:00.750
To give an example, a row with a time of 2014-09-01 01:00:00.333 would have a millisecond250 of 2014-09-01 01:00:00.250.
                                                                          |