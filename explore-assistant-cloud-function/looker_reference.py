"""
Looker API Reference Documentation for LLM Context
This module contains comprehensive Looker documentation to provide rich context for explore parameter generation.
"""

LOOKER_API_DOCUMENTATION = """# Looker API Documentation

## Query Object Format
| Field              | Type     | Description                                                                                                                                                  |
|--------------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|
| model              | string   | Model name                                                                                                                                                   |
| view               | string   | Explore name                                                                                                                                                 |
| fields             | string[] | Fields to include in query                                                                                                                                   |
| pivots             | string[] | Dimensions to pivot on (turns dimension values into columns)                                                                                                |
| fill_fields        | string[] | Fields to fill with default values                                                                                                                          |
| filters            | object   | Filters to apply (field_name: filter_expression)                                                                                                            |
| filter_expression  | string   | Global filter expression                                                                                                                                     |
| sorts              | string[] | Sort specifications (field_name, field_name+desc)                                                                                                           |
| limit              | string   | Maximum rows to return                                                                                                                                       |
| column_limit       | string   | Maximum columns for pivots (1-200)                                                                                                                          |
| total              | boolean  | Show column totals                                                                                                                                           |
| row_total          | string   | Show row totals ("right")                                                                                                                                    |
| subtotals          | string[] | Subtotal specifications                                                                                                                                      |
| vis_config         | object   | Visualization configuration with "type" property                                                                                                             |

## Filter Syntax Reference

### String Filters
- `value` = exact match (e.g., `FOO`)
- `value1,value2` = match either value (e.g., `FOO,BAR`)
- `%value%` = contains value (e.g., `%FOO%` matches "buffoon")
- `value%` = starts with value (e.g., `FOO%` matches "food")
- `%value` = ends with value (e.g., `%FOO` matches "buffoo")
- `EMPTY` = string is empty or null
- `NULL` = value is null
- `-value` = not equal to value (e.g., `-FOO`)
- `-%value%` = doesn't contain value (e.g., `-%FOO%`)
- `-value%` = doesn't start with value (e.g., `-FOO%`)
- `-%value` = doesn't end with value (e.g., `-%FOO`)
- `-EMPTY` = string is not empty
- `-NULL` = value is not null

### Date and Time Filters
- `this month` = data from current month
- `3 days` = last 3 days including current day
- `3 days ago` = the day that was 3 days ago
- `3 days ago for 2 days` = 2-day period starting 3 days ago
- `before 3 days ago` = all dates before 3 days ago
- `before 2023-01-01` = all dates before Jan 1, 2023
- `after 2023-01-01` = Jan 1, 2023, and all dates after
- `2023-01-01 to 2023-01-31` = date range (inclusive start, exclusive end)
- `2023-01-01 for 10 days` = 10-day period starting Jan 1, 2023
- `today` = current day

## Pivots

### When to use pivots
Use pivots to compare a measure across dimensions by turning a selected dimension into columns. If there are two dimensions requested, pivot on the one with lower cardinality. If a time dimension is used with any other dimension, pivot on the other dimension.

For time dimensions, always pivot by the less granular dimension:
- For "daily sales by week" → pivot by week
- For "monthly sales by quarter" → pivot by quarter
- For "monthly sales by year" → pivot by year

### URL Parameters for Pivots
- `pivots=view.field` = dimension to pivot on
- `limit=50` = max rows (default: 5000)
- `column_limit=20` = max columns in pivot (range: 1-200)
- `total=true` = display column totals
- `row_total=right` = display row totals on the right (only with pivots)
- `sorts=view.field1,view.count+desc` = sort order (use +desc for descending)

## Visualization Types
- `single_value` = single number display (use when a single number is requested)
- `table` = data table
- `looker_grid` = formatted grid
- `looker_column` = column chart
- `looker_bar` = bar chart
- `looker_line` = line chart
- `looker_area` = area chart
- `looker_pie` = pie chart
- `looker_scatter` = scatter plot
- `looker_map` = geographic map

### Chart Config Customization 
For customizing Cartesian charts (column, bar, line):

1. **Colors**
   - Background: `chart.backgroundColor`
   - Axis text: `xAxis.labels.style.color`, `yAxis.labels.style.color`
   - Tooltip: `tooltip.backgroundColor`, `tooltip.style.color`

2. **Conditional Formatting**
   Using `series.formatters` with `select` and `style` attributes:
   
   ```json
   {{
     "series": [{{
       "formatters": [{{
         "select": "value > 380", 
         "style": {{"color": "#FF9900"}}
       }}]
     }}]
   }}
   ```

   Select options:
   - `value` = series value
   - `max` = maximum value
   - `min` = minimum value
   - `percent_rank` = percentile
   - `name` = dimension value

Use proper JSON formatting when customizing chart configurations.
"""

def get_system_prompt_template(explore_key: str) -> str:
    """
    Get the system prompt template with comprehensive Looker documentation.
    
    Args:
        explore_key: The explore key in format "model:explore"
        
    Returns:
        System prompt template string with placeholders for query, table_context, and example_text
    """
    template = """# Looker Explore Parameter Generation

## Task
Generate Looker explore parameters for: "{query}"

""" + LOOKER_API_DOCUMENTATION + """

{table_context}

{example_text}

## Instructions
1. Choose only fields from the Available Dimensions and Measures above
2. Use proper filter syntax from the reference documentation
3. Select appropriate visualization type for the request
4. Include pivots when comparing measures across dimensions
5. Use proper date filter syntax for time-based queries
6. Return complete JSON structure with all required fields

## Response Format
Return ONLY this JSON structure:
{{
  "explore_key": \"""" + explore_key + """\",
  "explore_params": {{
    "fields": ["field1", "field2"],
    "filters": {{}},
    "sorts": ["field1"],
    "limit": "500",
    "vis_config": {{"type": "table"}}
  }},
  "message_type": "explore",
  "summary": "Brief description"
}}
"""
    return template