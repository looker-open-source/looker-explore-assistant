# Expanded URL generation

JSON Payload Fields:

fields: fields=view.field_1,view.field_2,view.count
 This parameter specifies the list of fields to be included in the results. In this example, the explore will return data for view.field_1, view.field_2, and the count of rows (view.count).

f[]: &f[view.filter_1_dimension]={{ value }} & &f[view.filter_2_on_date]=last+60+days
 This parameter defines filters for the explore. The f[] syntax is used to declare a filter on a specific dimension (view.filter_1_dimension and view.filter_2_on_date in this case). The {{ value }} placeholder indicates a dynamic value that can be passed through the URL. The second filter uses a Looker expression (last+60+days) to filter data for the past 60 days.

pivots: pivots=view.field_2 This parameter defines the dimension to pivot on. In this example, view.field_2 will be used to create a pivot table.

limit: limit=50 This parameter sets the maximum number of rows to be returned by the explore. The default limit is 5000, but here it's explicitly set to 50.

column_limit: column_limit=20 This parameter sets the maximum number of columns to be displayed in the pivot table. This parameter only has an effect when a pivot dimension is specified (as seen with pivots). The column_limit can be between 1 and 200. Dimensions, dimension table calculations, row total columns, and measure table calculations outside of pivots are not counted toward the column limit. Pivoted groups each count as one column toward the column limit.

total: total=true This parameter controls whether to display column totals in the explore results. Here, true indicates that column totals will be shown.

row_total: row_total=right This parameter controls whether to display row totals in the explore results. Here, right specifies that the row totals will be displayed on the right side. Only use row totals if the chart contains pivots.

sorts: sorts=view.field_1,view.count+desc This parameter defines the order in which the results should be sorted. The first field (view.field_1) is sorted by default in ascending order. The second sort (view.count+desc) sorts the results by view.count in descending order. The +desc syntax specifies descending order.

filter_config: The filter_config parameter contains detailed JSON objects that control the filtering aspects of the query. The filter_config represents the state of the filter UI on the explore page for a given query. When running a query via the Looker UI, this parameter takes precedence over "filters". 

Vis:  The vis parameter contains detailed JSON objects that control the visualization properties of the query. These properties are typically opaque and differ based on the type of visualization used. There is no specified set of allowed keys. The values can be any type supported by JSON. A "type" key with a string value is often present, and is used by Looker to determine which visualization to present. Visualizations ignore unknown vis_config properties.

Query_timezone: User's timezone, string value.

Subtotals: When using a table visualization and your data table contains at least two dimensions, you can apply subtotals. Subtotals are not available when you filter on a measure or when the Explore uses the sql_always_having parameter. List of fields to run the subtotals. The leftmost subtotal is always sorted. When you sort by multiple columns, subtotal columns are given precedence. Fields on which to run subtotals. 

# Pivot table reference

In Looker, pivots allow you to turn a selected dimension into several columns, which creates a matrix of your data similar to a pivot table in spreadsheet software. This is very useful for analyzing metrics by different groupings of your data, such as getting counts for category or label in your dataset.

When you pivot on a dimension, each unique possible value of that dimension becomes its own column header. Any measures are then repeated under each column header. 

Pivots make it much easier to compare a measure accross dimensions. It also shows you gaps in your data, where you don’t have any numeric values for a particular dimension field. In summary, pivots allow you to create and display a matrix of your data, similar to a pivot table in spreadsheet software. Specifically, pivots turn a selected dimension into several columns and are applied only to the visual display of your results.

With pivots, Looker allows you to regroup your data, so that you can easily compare results by different groupings and identify potential gaps, all while leaving your underlying data unaffected.

Whenever you have a question involving one dimension “by” another dimension, that’s a clue that a pivot might come in handy.

When two time dimensions are in a report and a pivot is required, always pivot by the least granular time dimension. 

|Example                                                                   | Pivoted Dimension                |
|--------------------------------------------------------------------------|----------------------------------|
| What were the hourly total sales by day in the past 3 days?              | Day                              |
| What were the daily total sales by week in the past 3 weeks?             | Week                             |
| What were the total sales by day each week in the past 2 weeks?          | Week                             |
| What were the total sales by day of week each week in the past 2 weeks?  | Week                             |
| What were the weekly total sales by month in the past 2 months?          | Month                            |
| What were the monthly total sales by quarter in the past 2 quarters?     | Quarter                          |
| What were the monthly total sales by quarter in the past 2 years?        | Year                             |
| What were the total sales by week of year each year in the past 2 years? | Year                             |
| What were the monthly total sales by year in the past 2 years?           | Year                             |
| What were the weekly total sales by quarter in the past 3 years?         | Quarter                          |

# Looker API JSON Fields

|application/JSON          |    Datatype            | Description
|--------------------------|------------------------|------------------------------------------------------------------------------------------
| can                      | Hash[boolean]          | Operations the current user is able to perform on this object
| id                       | string                 | Unique Id
| model                    | string                 | Model
| view                     | string                 | Explore Name
| fields                   | string[]               | Fields
| pivots                   | string[]               | Pivots
| fill_fields              | string[]               | Fill Fields
| filters                  | Hash[string]           | Filters will contain data pertaining to complex filters that do not contain "or" conditions. When "or" conditions are present, filter data will be found on the filter_expression property.
| filter_expression        | string                 | Filter Expression
| sorts                    | string[]               | Sorting for the query results. Use the format ["view.field", ...] to sort on fields in ascending order. Use the format ["view.field desc", ...] to sort on fields in descending order. Use ["__UNSORTED__"] (2 underscores before and after) to disable sorting entirely. Empty sorts [] will trigger a default sort.
| limit                    | string                 | Row limit. To download unlimited results, set the limit to -1 (negative one).
| column_limit             | string                 | Column Limit
| total                    | boolean                | Total
| row_total                | string                 | Raw Total
| subtotals                | string[]               | Fields on which to run subtotals
| vis_config               | Hash[any]              | Visualization configuration properties. These properties are typically opaque and differ based on the type of visualization used. There is no specified set of allowed keys. The values can be any type supported by JSON. A "type" key with a string value is often present, and is used by Looker to determine which visualization to present. Visualizations ignore unknown vis_config properties.
| filter_config            | Hash[any]              | The filter_config represents the state of the filter UI on the explore page for a given query. When running a query via the Looker UI, this parameter takes precedence over "filters". When creating a query or modifying an existing query, "filter_config" should be set to null. Setting it to any other value could cause unexpected filtering behavior. The format should be considered opaque.
| visible_ui_sections      | string                 | Visible UI Sections
| slug                     | string                 | Slug
| dynamic_fields           | string                 | Dynamic Fields
| client_id                | string                 | Client Id: used to generate shortened explore URLs. If set by client, must be a unique 22 character alphanumeric string. Otherwise one will be generated.
| share_url                | string                 | Share Url
| expanded_share_url       | string                 | Expanded Share Url
| url                      | string                 | Expanded Url
| query_timezone           | string                 | Query Timezone
| has_table_calculations   | boolean                | Has Table Calculations
                                                                          |