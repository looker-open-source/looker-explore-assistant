from urllib.parse import urlsplit, quote, unquote, parse_qs, urlencode
import re


def parse_url(query_data):
    parsed_url = parse_qs(urlsplit(query_data).query)

    # reconstruct url for training data
    decoded_url_modifiedvisjson = ''
    # return url parameters as a string
    for query_param in parsed_url.items():
        # parse fields
        if query_param[0] == 'fields':
            decoded_url_modifiedvisjson += f'fields={query_param[1][0]}'
        # parse limit
        if query_param[0] == 'limit':
            decoded_url_modifiedvisjson += f'&limit={query_param[1][0]}'
        # parse column limit
        if query_param[0] == 'column_limit':
            decoded_url_modifiedvisjson += f'&column_limit={query_param[1][0]}'
        # parse filters
        if query_param[0].startswith('f['):
            decoded_url_modifiedvisjson += f'&{query_param[0]}={query_param[1][0]}'
        # parse pivots
        if query_param[0] == 'pivots':
            decoded_url_modifiedvisjson += f'&pivots={query_param[1][0]}'
        # parse fill fields
        if query_param[0] == 'fill_fields':
            decoded_url_modifiedvisjson += f'&fill_fields={query_param[1][0]}'
        # parse dynamic fields ie. custom fields and table calcs
        if query_param[0] == 'dynamic_fields':
            decoded_url_modifiedvisjson += f'&dynamic_fields={query_param[1][0]}'
        # parse sorts
        if query_param[0] == 'sorts':
            decoded_url_modifiedvisjson += f'&sorts={query_param[1][0]}'
        # parse just vis type
        if query_param[0] == 'vis':
            vis_type = re.search(r'("type":\s*"([^,}]+))', query_param[1][0])
            if vis_type:
                decoded_url_modifiedvisjson += '&vis={' + vis_type.group(1) + '}'
            # if no vis type, don't add
            else:
                continue
        # if none of the above skip as it's not needed
        else:
            continue

    print(f"""Components of your url: \n {parsed_url}\nReconstructed url for Explore Assistant (copy this): \n {decoded_url_modifiedvisjson}""")


def generate_expanded_url(processed_url):
    base_url = "https://canonusa.cloud.looker.com/explore/cusa-nlp/order"
    origin = "&origin=share-expanded"

    processed_url = "?" + processed_url
    # Parse the processed URL into components
    parsed_url = urlsplit(processed_url)
    query_params = parse_qs(parsed_url.query)

    # Reconstruct the query string with encoded parameter values
    encoded_query = urlencode(query_params, doseq=True)

    # Combine base URL, processed URL, and origin
    expanded_url = base_url + '?' + encoded_query + origin
    return expanded_url


if __name__ == "__main__":
    # url = "/explore/cusa-nlp/order?fields=order.total_product_amount,product.group_0_name&f[order.placed_date]=3+months&sorts=order.total_product_amount+desc+0&limit=500&column_limit=50&vis=%7B%22x_axis_gridlines%22%3Afalse%2C%22y_axis_gridlines%22%3Atrue%2C%22show_view_names%22%3Afalse%2C%22show_y_axis_labels%22%3Atrue%2C%22show_y_axis_ticks%22%3Atrue%2C%22y_axis_tick_density%22%3A%22default%22%2C%22y_axis_tick_density_custom%22%3A5%2C%22show_x_axis_label%22%3Atrue%2C%22show_x_axis_ticks%22%3Atrue%2C%22y_axis_scale_mode%22%3A%22linear%22%2C%22x_axis_reversed%22%3Afalse%2C%22y_axis_reversed%22%3Afalse%2C%22plot_size_by_field%22%3Afalse%2C%22trellis%22%3A%22%22%2C%22stacking%22%3A%22%22%2C%22limit_displayed_rows%22%3Afalse%2C%22legend_position%22%3A%22center%22%2C%22point_style%22%3A%22none%22%2C%22show_value_labels%22%3Afalse%2C%22label_density%22%3A25%2C%22x_axis_scale%22%3A%22auto%22%2C%22y_axis_combined%22%3Atrue%2C%22ordering%22%3A%22none%22%2C%22show_null_labels%22%3Afalse%2C%22show_totals_labels%22%3Afalse%2C%22show_silhouette%22%3Afalse%2C%22totals_color%22%3A%22%23808080%22%2C%22hidden_points_if_no%22%3A%5B%22xd%22%2C%22showinbetweenquantiles%22%5D%2C%22type%22%3A%22looker_bar%22%2C%22defaults_version%22%3A1%2C%22hidden_pivots%22%3A%7B%7D%2C%22series_types%22%3A%7B%7D%2C%22hidden_fields%22%3A%5B%22percentile%22%2C%22percentile_1%22%5D%7D&filter_config=%7B%22order.placed_date%22%3A%5B%7B%22type%22%3A%22past%22%2C%22values%22%3A%5B%7B%22constant%22%3A%223%22%2C%22unit%22%3A%22mo%22%7D%2C%7B%7D%5D%2C%22id%22%3A3%2C%22error%22%3Afalse%7D%5D%7D&dynamic_fields=%5B%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22percentile%28%24%7Border.total_product_amount%7D%2C0.25%29%22%2C%22label%22%3A%2225_percentile%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22percentile%22%2C%22_type_hint%22%3A%22number%22%7D%2C%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22percentile%28%24%7Border.total_product_amount%7D%2C0.75%29%22%2C%22label%22%3A%2275_percentile%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22percentile_1%22%2C%22_type_hint%22%3A%22number%22%7D%2C%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22%24%7Border.total_product_amount%7D+%3E%3D%24%7Bpercentile%7D+AND+%24%7Border.total_product_amount%7D+%3C%3D%24%7Bpercentile_1%7D%22%2C%22label%22%3A%22showinbetweenquantiles%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22showinbetweenquantiles%22%2C%22_type_hint%22%3A%22yesno%22%7D%5D"
    # url = "https://canonusa.cloud.looker.com/explore/cusa-nlp/order?fields=order.total_product_amount%2Cproduct.group_0_name&f%5Border.placed_date%5D=3+months&sorts=order.total_product_amount+desc+0&limit=500&column_limit=50&vis=%7B%22type%22%3A%22looker_bar%22%2C%22hidden_fields%22%3A%5B%22percentile%22%2C%22percentile_1%22%5D%2C%22hidden_points_if_no%22%3A%5B%22xd%22%2C%22showinbetweenquantiles%22%5D%7D&dynamic_fields=%5B%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22percentile%28%24%7Border.total_product_amount%7D%2C0.25%29%22%2C%22label%22%3A%2225_percentile%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22percentile%22%2C%22_type_hint%22%3A%22number%22%7D%2C%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22percentile%28%24%7Border.total_product_amount%7D%2C0.75%29%22%2C%22label%22%3A%2275_percentile%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22percentile_1%22%2C%22_type_hint%22%3A%22number%22%7D%2C%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22%24%7Border.total_product_amount%7D+%3E%3D%24%7Bpercentile%7D+AND+%24%7Border.total_product_amount%7D+%3C%3D%24%7Bpercentile_1%7D%22%2C%22label%22%3A%22showinbetweenquantiles%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22showinbetweenquantiles%22%2C%22_type_hint%22%3A%22yesno%22%7D%5D&origin=share-expanded"
    url = "https://canonusa.cloud.looker.com/explore/cusa-nlp/order?fields=order.total_product_amount,product.group_0_name&f[order.placed_date]=3+months&sorts=order.total_product_amount+desc+0&limit=500&column_limit=50&vis=%7B%22x_axis_gridlines%22%3Afalse%2C%22y_axis_gridlines%22%3Atrue%2C%22show_view_names%22%3Afalse%2C%22show_y_axis_labels%22%3Atrue%2C%22show_y_axis_ticks%22%3Atrue%2C%22y_axis_tick_density%22%3A%22default%22%2C%22y_axis_tick_density_custom%22%3A5%2C%22show_x_axis_label%22%3Atrue%2C%22show_x_axis_ticks%22%3Atrue%2C%22y_axis_scale_mode%22%3A%22linear%22%2C%22x_axis_reversed%22%3Afalse%2C%22y_axis_reversed%22%3Afalse%2C%22plot_size_by_field%22%3Afalse%2C%22trellis%22%3A%22%22%2C%22stacking%22%3A%22%22%2C%22limit_displayed_rows%22%3Afalse%2C%22legend_position%22%3A%22center%22%2C%22point_style%22%3A%22none%22%2C%22show_value_labels%22%3Afalse%2C%22label_density%22%3A25%2C%22x_axis_scale%22%3A%22auto%22%2C%22y_axis_combined%22%3Atrue%2C%22ordering%22%3A%22none%22%2C%22show_null_labels%22%3Afalse%2C%22show_totals_labels%22%3Afalse%2C%22show_silhouette%22%3Afalse%2C%22totals_color%22%3A%22%23808080%22%2C%22hidden_points_if_no%22%3A%5B%22xd%22%2C%22showinbetweenquantiles%22%5D%2C%22type%22%3A%22looker_bar%22%2C%22defaults_version%22%3A1%2C%22hidden_pivots%22%3A%7B%7D%2C%22series_types%22%3A%7B%7D%2C%22hidden_fields%22%3A%5B%22percentile%22%2C%22percentile_1%22%5D%7D&filter_config=%7B%22order.placed_date%22%3A%5B%7B%22type%22%3A%22past%22%2C%22values%22%3A%5B%7B%22constant%22%3A%223%22%2C%22unit%22%3A%22mo%22%7D%2C%7B%7D%5D%2C%22id%22%3A3%2C%22error%22%3Afalse%7D%5D%7D&dynamic_fields=%5B%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22percentile%28%24%7Border.total_product_amount%7D%2C0.25%29%22%2C%22label%22%3A%2225_percentile%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22percentile%22%2C%22_type_hint%22%3A%22number%22%7D%2C%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22percentile%28%24%7Border.total_product_amount%7D%2C0.75%29%22%2C%22label%22%3A%2275_percentile%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22percentile_1%22%2C%22_type_hint%22%3A%22number%22%7D%2C%7B%22category%22%3A%22table_calculation%22%2C%22expression%22%3A%22%24%7Border.total_product_amount%7D+%3E%3D%24%7Bpercentile%7D+AND+%24%7Border.total_product_amount%7D+%3C%3D%24%7Bpercentile_1%7D%22%2C%22label%22%3A%22showinbetweenquantiles%22%2C%22value_format%22%3Anull%2C%22value_format_name%22%3Anull%2C%22_kind_hint%22%3A%22measure%22%2C%22table_calculation%22%3A%22showinbetweenquantiles%22%2C%22_type_hint%22%3A%22yesno%22%7D%5D&origin=share-expanded"
    parse_url(url)
    # expanded_url = generate_expanded_url(processed_url)
    # print(expanded_url)