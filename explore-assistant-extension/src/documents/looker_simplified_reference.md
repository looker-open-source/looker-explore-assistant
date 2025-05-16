# Looker Simplified Reference

This document provides essential formats and values for Looker filters, pivots, and visualizations, designed as context for LLM agents.

## Filters

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
Common formats:
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

## Visualizations

### Common Visualization Types
- Column
- Bar
- Line
- Area
- Pie
- Scatter
- Map
- Table
- Single value

Choose 'Single value' if a single number is requested.

### Chart Config Customization 
For customizing Cartesian charts (column, bar, line):

1. **Colors**
   - Background: `chart.backgroundColor`
   - Axis text: `xAxis.labels.style.color`, `yAxis.labels.style.color`
   - Tooltip: `tooltip.backgroundColor`, `tooltip.style.color`

2. **Conditional Formatting**
   Using `series.formatters` with `select` and `style` attributes:
   
   ```json
   {
     "series": [{
       "formatters": [{
         "select": "value > 380", 
         "style": {"color": "#FF9900"}
       }]
     }]
   }
   ```

   Select options:
   - `value` = series value
   - `max` = maximum value
   - `min` = minimum value
   - `percent_rank` = percentile
   - `name` = dimension value

Use proper JSON formatting when customizing chart configurations.
