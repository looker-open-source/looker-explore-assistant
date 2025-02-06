
# Looker Visualization Config Documentation


## Customizing Visualizations Using the Chart Config Editor

You can use the Chart Config Editor to customize formatting options on Looker visualizations that use the HighCharts API. This includes most Cartesian charts, such as the column chart, bar chart, and line chart, among others.

### Prerequisites

To access the Chart Config Editor, you must have the `can_override_vis_config` permission.

### Customizing a Visualization

To customize a visualization with the Chart Config Editor, follow these steps:

1. **View or Edit a Visualization**: 
   - View a visualization in an Explore, or edit a visualization in a Look or dashboard.
   
2. **Open the Chart Config Editor**:
   - Open the Edit menu in the visualization.
   - Click the **Edit Chart Config** button in the Plot tab. Looker displays the Edit Chart Config dialog.

3. **Modify the JSON**:
   - The **Chart Config (Source)** pane contains the original JSON of your visualization and cannot be edited.
   - The **Chart Config (Override)** pane contains the JSON that should override the source JSON. When you first open the Edit Chart Config dialog, Looker populates the pane with some default JSON. You can start with this JSON or delete it and enter any valid HighCharts JSON.
   - Select the Chart Config (Override) section and enter valid HighCharts JSON. The new values will override any values in the Chart Config (Source) section.

4. **Format and Apply Changes**:
   - Click `<>` (Format code) to allow Looker to properly format your JSON.
   - Click **Preview** to test your changes.
   - Click **Apply** to apply your changes. The visualization will be displayed using the custom JSON values.

5. **Save the Visualization**:
   - Once you've customized your visualization, save it. If you viewed the visualization in an Explore, save the Explore. If you edited a Look or a dashboard, click Save.

### Caution

Do not edit the default visualization options after making changes in the Chart Config Editor. Editing the default visualization options may cause unexpected behavior, including blank visualizations. If you'd like to edit the default visualization options, first remove any changes you've made in the Chart Config Editor, then replace them later. Specifically, follow these steps:

1. Click the **Edit Chart Config** button in the Plot tab. Looker displays the Edit Chart Config dialog.
2. Copy the text in the Chart Config (Override) pane.
3. Click the **Clear Chart Overrides** button to delete all changes.
4. Click **Apply**.
5. Edit your visualization using the default visualization options.
6. Click the **Edit Chart Config** button in the Plot tab. Looker displays the Edit Chart Config dialog.
7. Enter some valid HighCharts JSON in the Chart Config (Override) pane. You can use the text that you copied in step 2 as a template, but be sure to test your changes using the Preview button to ensure there are no conflicts.
8. Click **Apply**.

### Conditional Formatting with Series Formatters

The Chart Config Editor accepts most valid HighCharts JSON. It also accepts the `series.formatters` attribute, which only exists in Looker. Each series can have multiple formatters to combine different style rules.

The `series.formatters` attribute accepts two attributes: `select` and `style`.

- Enter a logical expression in the `select` attribute to indicate which data values will be formatted.
- Enter some JSON into the `style` attribute to indicate how to format the data values.

For example, the following JSON will color each data value orange if it is greater than or equal to 380:

```json
{
  "series": [{
    "formatters": [{
      "select": "value >= 380",
      "style": {
        "color": "orange"
      }
    }]
  }]
}
```

#### The `select` Attribute

You can use the following values in a `select` expression:

- `value`: This variable returns the value of the series. For example, you could use `select: value > 0` to target all positive values, or `value = 100` to only match series with a value of 100.
- `max`: Use `select: max` to target the series value that has the maximum value.
- `min`: Use `select: min` to target the series value that has the minimum value.
- `percent_rank`: This variable targets the series value with a specified percentile. For example, you could use `select: percent_rank >= 0.9` to target series values in the ninetieth percentile.
- `name`: This variable returns the dimension value of the series. For example, if you had a report showing Sold, Canceled, and Returned orders, you could use `select: name = Sold` to target the series where the dimension value is Sold.
- `AND/OR`: Use `AND` and `OR` to combine multiple logical expressions.

#### The `style` Attribute

The `style` attribute can be used to apply styles that HighCharts supports. For example, you can color series values using `style.color`, color series borders using `style.borderColor`, and set series border width using `style.borderWidth`. For a more complete list of style options, see the Highcharts options for `series.column.data`.

For line visualizations, use `style.marker.fillColor` and `style.marker.lineColor` instead of `style.color`. For a more complete list of line style options, see the Highcharts options for `series.line.data.marker`.

### Examples

The following sections provide examples of some common use cases for the Chart Config Editor. For a complete list of the attributes that you can edit, see the [HighCharts API documentation](https://api.highcharts.com/highcharts/).

#### Change the Background Color and Axis Text Color

To change the background color of a visualization, use the `chart.backgroundColor` attribute.

Similarly, to change the text color of the axes in a visualization, use the following attributes:

- `xAxis.labels.style.color`
- `xAxis.title.style.color`
- `yAxis.labels.style.color`
- `yAxis.title.style.color`

The following HighCharts JSON changes the background color of the visualization to purple, and the text of the axis titles and labels to white.

```json
{
  "chart": {
    "backgroundColor": "purple"
  },
  "xAxis": {
    "labels": {
      "style": {
        "color": "white"
      }
    },
    "title": {
      "style": {
        "color": "white"
      }
    }
  },
  "yAxis": {
    "labels": {
      "style": {
        "color": "white"
      }
    },
    "title": {
      "style": {
        "color": "white"
      }
    }
  }
}
```

#### Customize Tooltip Color

To customize the color of the tooltip, use the following attributes:

- `tooltip.backgroundColor`
- `tooltip.style.color`

The following HighCharts JSON changes the background color of the tooltip to cyan, and changes the color of the tooltip text to black.

```json
{
  "tooltip": {
    "backgroundColor": "cyan",
    "style": {
      "color": "black"
    }
  }
}
```

#### Customize Tooltip Content and Styles

To customize the content of the tooltip, use the following attributes:

- `tooltip.format`
- `tooltip.shared`

The following HighCharts JSON changes the tooltip format such that the x-axis value appears at the top of the tooltip in larger font, followed by a list of all series values at that point.

This example uses the following HighCharts functions and variables:

- `{key}` is a variable that returns the x-axis value of the selected point. (in this example, the month and year).
- `{#each points}{/each}` is a function that repeats the enclosed code for each series in the chart.
- `{series.name}` is a variable that returns the name of the series.
- `{y:.2f}` is a variable that returns the y-axis value of the selected point, rounded to two decimal places.
- `{y}` is a variable that returns the y-axis value of the selected point.
- `{variable:.2f}` rounds `variable` to two decimal places. See the [Highcharts templating documentation](https://api.highcharts.com/highcharts/tooltip.formatter) for more examples of value formatting.

```json
{
  "tooltip": {
    "format": "<span style=\"font-size: 1.8em\">{key}</span><br/>{#each points}<span style=\"color:{color}; font-weight: bold;\">\\u25CF {series.name}: </span>{y:.2f}<br/>{/each}",
    "shared": true
  }
}
```

#### Add Chart Annotations and Captions

To add an annotation, use the `annotations` attribute. To add a caption to the chart, use the `caption` attribute.

To get the coordinates for a point, click **Inspect Point Metadata** at the top of the Edit Chart Config dialog. Then, hold the pointer over the data point that you'd like to annotate. Looker displays a point ID, which you can use in the `annotations.labels.point` attribute.

The following HighCharts JSON adds two annotations to the chart to explain a decrease in inventory items after certain periods of time. It also adds a caption to the bottom of the chart to explain the annotations in more detail.

```json
{
  "caption": {
    "text": "Items go on clearance after 60 days, and are thrown away after 80 days. Thus we see large drops in inventory after these events."
  },
  "annotations": [{
    "labels": [{
        "point": "inventory_items.count-60-

79",
        "text": "Clearance sale"
      },
      {
        "point": "inventory_items.count-80+",
        "text": "Thrown away"
      }
    ]
  }]
}
```

#### Add Vertical Reference Bands

To add a vertical reference band, use the `xAxis.plotBands` attribute.

The following HighCharts JSON adds a vertical reference band between November 24, 2022 and November 29, 2022 to denote a sale period. It also adds a caption to the bottom of the chart to explain the significance of the band.

Note that the `to` and `from` attributes of `xAxis.plotBands` must correspond to data values in the chart. In this example, since the data is time-based, the attributes accept Unix timestamp values (1669680000000 for November 29, 2022 and 1669248000000 for November 24, 2022). String-based date formats like MM/DD/YYYY and DD-MM-YY are not supported in the `to` and `from` HighCharts attributes.

```json
{
  "caption": {
    "text": "This chart uses the HighCharts plotBands attribute to display a band around the Black Friday Cyber Monday sale period."
  },
  "xAxis": {
    "plotBands": [{
      "to": 1669680000000,
      "from": 1669248000000,
      "label": {
        "text": "BFCM Sale Period"
      }
    }]
  }
}
```

#### Color the Maximum, Minimum, and Percentile Values

See the [Getting the most out of Looker visualizations cookbook: Conditional formatting customization in Cartesian charts](https://cloud.google.com/looker/docs/visualizations-custom-chart-editor) page for an in-depth example about coloring the maximum, minimum, and percentile values of a Cartesian visualization.