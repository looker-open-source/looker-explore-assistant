import re
from urllib.parse import unquote

def process_url(url):
    decoded_url = unquote(url)

    # Return URL parameters as a string
    url_parameters = decoded_url.split("?", 1)[1].replace("+", " ")

    # Search for the dynamic_fields parameter
    dynamic_fields_match = re.search(r"dynamic_fields=(.*?)($|&)", url_parameters)
    dynamic_fields = None
    if dynamic_fields_match:
        dynamic_fields = dynamic_fields_match.group(1)
        if dynamic_fields == "[]":
            dynamic_fields = None

    # Remove timezone parameter
    decoded_url_notimezone = re.sub(
        r"&query_timezone=(.)*&", "&", url_parameters, count=1
    )

    # Remove filter config parameter
    decoded_url_nofilterconfig = re.sub(
        r"&filter_config=(.)*(?=&|$)", "&", decoded_url_notimezone
    )
    if decoded_url_nofilterconfig[-1] == "&":
        decoded_url_nofilterconfig = decoded_url_nofilterconfig[:-1]

    # Parse vis config parameter and only maintain vis type
    vis_config_match = re.search(r"&vis=(.*?)(?=&|$)", decoded_url_nofilterconfig)

    if vis_config_match:
        vis_json_str = vis_config_match.group(1)
        # Regex to search for the top-level vis type
        vis_type_match = re.search(r'"type":\s*"([^"]+)"(?!.*"type")', vis_json_str)
        hidden_fields_match = re.search(
            r'"hidden_fields":\s*(\[[^\]]*\])', vis_json_str
        )
        show_comparison_match = re.search(r'"show_comparison":\s*(true)', vis_json_str)
        comparison_type_match = re.search(
            r'"comparison_type":\s*"([^"]+)"', vis_json_str
        )
        hidden_points_if_no_match = re.search(
            r'"hidden_points_if_no":\s*(\[[^\]]*\])', vis_json_str
        )
        series_types_match = re.search(
            r'"series_types":\s*(\{[^\}]*\})', vis_json_str
        )

        vis_type = vis_type_match.group(1) if vis_type_match else ""
        hidden_fields = hidden_fields_match.group(1) if hidden_fields_match else "[]"
        hidden_points_if_no = (
            hidden_points_if_no_match.group(1) if hidden_points_if_no_match else "[]"
        )
        series_types = (
            series_types_match.group(1) if series_types_match else "{}"
        )

        # Construct the new vis config JSON string
        new_vis_config = f'&vis={{"type":"{vis_type}"'

        if hidden_fields != "[]":
            new_vis_config += f',"hidden_fields":{hidden_fields}'

        if show_comparison_match:
            new_vis_config += ',"show_comparison":true'
            if comparison_type_match:
                comparison_type = comparison_type_match.group(1)
                new_vis_config += f',"comparison_type":"{comparison_type}"'

        if hidden_points_if_no != "[]":
            new_vis_config += f',"hidden_points_if_no":{hidden_points_if_no}'

        if series_types != "{}":
            new_vis_config += f',"series_types":{series_types}'

        new_vis_config += '}'

        # Replace the vis config in the original URL parameter string with the modified vis config
        decoded_url_modifiedvisjson = re.sub(
            r"&vis=.*?(?=&|$)", new_vis_config, decoded_url_nofilterconfig
        )
    else:
        decoded_url_modifiedvisjson = decoded_url_nofilterconfig

    # Re-add dynamic fields if they were present
    if dynamic_fields:
        new_dynamic_fields = f"&dynamic_fields={dynamic_fields}"
        decoded_url_modifiedvisjson += new_dynamic_fields


    # Remove fill_fields parameter if it exists
    decoded_url_remove_fill_fields = re.sub(
        r"&fill_fields=(.*?)($|&)", "&", decoded_url_modifiedvisjson
    )

    if (decoded_url_remove_fill_fields[-1] == "&"):
        decoded_url_remove_fill_fields = decoded_url_remove_fill_fields[:-1]

    return decoded_url_remove_fill_fields


if __name__ == "__main__":
    # url = "/explore/cusa-nlp/order?fields=order.total_product_amount,product.group_0_name&f[order.placed_date]=3+months&sorts=order.total_product_amount+desc+0&limit=500&column_limit=50&vis=%7B%22x_axis_gridlines%22%3Afalse%2C%22y_axis_gridlines%22%3Atrue%2C%22show_view_names%22%3Afalse%2C%22show_y_axis_labels%22%3Atrue%2C%22show_y_axis_ticks%22%3Atrue%2C%22y_axis_tick_density%22%3A%22default%22%2C%22y_axis_tick_density_custom%22%3A5%2C%22show_x_axis_label%22%3Atrue%2C%22show_x_axis_ticks%22%3Atrue%2C%22y_axis_scale_mode%22%3A%22linear%22%2C%22x_axis_reversed%22%3Afalse%2C%22y_axis_reversed%22%3Afalse%2C%22plot_size_by_field%22%3Afalse%2C%22trellis%22%3A%22%22%2C%22stacking%22%3A%22%22%2C%22limit_displayed_rows%22%3Afalse%2C%22legend_position%22%3A%22center%22%2C%22point_style%22%3A%22none%22%2C%22show_value_labels%22%3Afalse%2C%22label_density%22%3A25%2C%22x_axis_scale%22%3A%22auto%22%2C%22y_axis_combined%22%3Atrue%2C%22ordering%22%3A%22none%22%2C%22show_null_labels%22%3Afalse%2C%22show_totals_labels%22%3Afalse%2C%22show_silhouette%22%3Afalse%2C%22totals_color%22%3A%22%23808080%22%2C%22hidden_points_if_no%22%3A%5B%22xd%22%2C%22showinbetweenquantiles%22%5D%2C%22type%22%3A%22looker_bar%22%2C%22defaults_version%22%3A1%2C%22hidden_pivots%22%3A%7B%7D%2C%22series_types%22%3A%7B%7D%2C%22hidden_fields%22%3A%5B%22percentile%22%2C%22percentile_1%22%5D%7D&filter_config=%7B%22order.placed_date%22%3A%5B%7B%22type%22%3A%22past%22%2C%22values%22%3A%5B%7B%22constant%22%3A%223%22%2C%22unit%22%3A%22mo%22%7D%2C%7B%7D%5D%2C%22id%22%3A3%2C%22error%22%3Afalse%7D%5D%7D&dynamic_fields=%5B%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22percentile%28%24%7Border.total_product_amount%7D%2C0.25%29%22%2C%22label%22%3A%2225_percentile%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22percentile%22%2C%22_type_hint%22%3A%22number%22%7D%2C%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22percentile%28%24%7Border.total_product_amount%7D%2C0.75%29%22%2C%22label%22%3A%2275_percentile%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22percentile_1%22%2C%22_type_hint%22%3A%22number%22%7D%2C%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22%24%7Border.total_product_amount%7D+%3E%3D%24%7Bpercentile%7D+AND+%24%7Border.total_product_amount%7D+%3C%3D%24%7Bpercentile_1%7D%22%2C%22label%22%3A%22showinbetweenquantiles%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22showinbetweenquantiles%22%2C%22_type_hint%22%3A%22yesno%22%7D%5D"
    url = "/explore/cusa-nlp/order?fields=order_line_item.total_net_amount,order_line_item.total_product_amount,order.placed_month&fill_fields=order.placed_month&f[order.store_entity_id]=85&f[order.placed_month]=12+month+ago+for+12+month&sorts=order.placed_month&limit=500&column_limit=50&vis=%7B%22x_axis_gridlines%22%3Afalse%2C%22y_axis_gridlines%22%3Atrue%2C%22show_view_names%22%3Afalse%2C%22show_y_axis_labels%22%3Atrue%2C%22show_y_axis_ticks%22%3Atrue%2C%22y_axis_tick_density%22%3A%22default%22%2C%22y_axis_tick_density_custom%22%3A5%2C%22show_x_axis_label%22%3Atrue%2C%22show_x_axis_ticks%22%3Atrue%2C%22y_axis_scale_mode%22%3A%22linear%22%2C%22x_axis_reversed%22%3Afalse%2C%22y_axis_reversed%22%3Afalse%2C%22plot_size_by_field%22%3Afalse%2C%22trellis%22%3A%22%22%2C%22stacking%22%3A%22%22%2C%22limit_displayed_rows%22%3Afalse%2C%22legend_position%22%3A%22center%22%2C%22point_style%22%3A%22none%22%2C%22show_value_labels%22%3Afalse%2C%22label_density%22%3A25%2C%22x_axis_scale%22%3A%22auto%22%2C%22y_axis_combined%22%3Atrue%2C%22ordering%22%3A%22none%22%2C%22show_null_labels%22%3Afalse%2C%22show_totals_labels%22%3Afalse%2C%22show_silhouette%22%3Afalse%2C%22totals_color%22%3A%22%23808080%22%2C%22type%22%3A%22looker_column%22%2C%22show_null_points%22%3Atrue%2C%22interpolation%22%3A%22linear%22%2C%22defaults_version%22%3A1%2C%22series_types%22%3A%7B%7D%7D&filter_config=%7B%22order.store_entity_id%22%3A%5B%7B%22type%22%3A%22%3D%22%2C%22values%22%3A%5B%7B%22constant%22%3A%2285%22%7D%2C%7B%7D%5D%2C%22id%22%3A8%7D%5D%2C%22order.placed_month%22%3A%5B%7B%22type%22%3A%22advanced%22%2C%22values%22%3A%5B%7B%22constant%22%3A%2212+month+ago+for+12+month%22%7D%2C%7B%7D%5D%2C%22id%22%3A9%7D%5D%7D"
    processed_url = process_url(url)
    print(processed_url)
