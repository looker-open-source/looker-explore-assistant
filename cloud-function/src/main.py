import functions_framework
import vertexai
import os
from urllib.parse import urlparse, parse_qs
import json
import re

def tokenizer(text):
    """
    Tokenizes the given text into a list of words.

    Args:
        text (str): The text to be tokenized.

    Returns:
        list: A list of words extracted from the text.
    """
    pattern = re.compile('\w+')
    matches = pattern.finditer(text)
    return list(matches)

@functions_framework.http
def gen_looker_query(request):
    """
    Generate Looker query based on the given request.

    Args:
        request (flask.Request): The HTTP request object.

    Returns:
        tuple: A tuple containing the response body, status code, and headers.
    """

    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600"
        }

        return ("", 204, headers)

    project = os.environ.get("PROJECT")
    location = os.environ.get("REGION")


    vertexai.init(project=project, location=location)
    parameters = {
        "temperature": 0.2,
        "max_output_tokens": 100,### Reduce token to avoid having multiples results on the same request
        "top_p": 0.8,
        "top_k": 40
    }

    context = """You\'re a developer who would transalate questions to a structured URL query based on the following json of fields - choose only the fields in the below description using the field "name" in the url. Make sure a limit of 500 or less is always applied.: \n
    """

    examples = """\n The examples here showcase how the url should be constructed. Only use the "dimensions" and "measures" above for fields, filters and sorts
    input: customer with lifetime revenue > 100
    output :fields=user_order_facts.lifetime_revenue&f[user_order_facts.lifetime_revenue]=>100&sorts=user_order_facts.lifetime_revenue desc 0&limit=500

    input : Customer who are currently active and made an order in the last day 30 days
    output :fields=users.email,order_items.created_date&f[user_order_facts.currently_active_customer]=Yes&f[order_items.created_date]=last 30 days&sorts=order_items.created_date desc


    input: What s the total sales of brand Calvin Klein?
    output:fields=order_items.total_sale_price&f[products.brand]=Calvin Klein&vis={"type":"single_value"}

    input: Orders that are still in Processing after 3 days, filtered by Distribution Center
    output:fields=order_items.created_date,order_items.order_id,products.item_name,order_items.status,users.email,order_items.average_days_to_process&f[distribution_centers.name]=Chicago IL&f[order_items.created_date]=before 3 days ago&f[order_items.status]=Processing&sorts=order_items.created_date desc&column_limit=50&vis={"type":"looker_grid"}

    input: What\'s my sales for the last two years ? plot as bar chart
    output:fields=order_items.total_sale_price&f[order_items.created_date]=2 years&sorts=order_items.total_sale_price descvis={"type":"looker_bar"}

    input: Severely delayed orders in Chicaco
    output:fields=order_items.created_date,order_items.order_id,products.item_name,order_items.status,users.email,order_items.average_days_to_process&f[distribution_centers.name]=Chicago IL&f[order_items.created_date]=before 3 days ago&f[order_items.status]=Processing&column_limit=50

    input: 30 Day Repeat Purchase Rate by Brand, column chart
    output:fields=order_items.30_day_repeat_purchase_rate,products.brand&f[products.brand]=&sorts=order_items.30_day_repeat_purchase_rate desc 0&limit=500&vis={"type":"looker_column"}

    input: Top 10 Brand by Sales
    output:fields=products.brand,order_items.total_sale_price&sorts=order_items.total_sale_price desc 0&limit=10&column_limit=50

    input: What\'s my sales for last 4 months by category ? plot as area
    output:fields=products.category,order_items.total_sale_price&f[order_items.created_date]=4 months&limit=500&vis={"type":"single_value"}

    input: repeat purchase rate by category, plot as  pie
    output:fields=order_items.30_day_repeat_purchase_rate,products.category&vis={"type":"looker_pie"}

    input: average order sales by category, as bar chart
    output:fields=order_items.average_sale_price,products.category&vis={"type":"looker_bar"}

    input: users whith lifetime value > 100$ and made more than 4 orders, as table
    output:fields=users.lifetime_revenue,users.lifetime_orders&f[users.lifetime_revenue]=>100&f[users.lifetime_orders]=>4&sorts=users.lifetime_revenue desc 0&vis={"type":"looker_grid"}

    input: sales for Columbia, Levi's and Nike this year, as bar chart
    output:fields=products.brand,order_items.total_sale_price&f[products.brand]=Columbia,"Levi's", Nike&f[order_items.created_date]=this year&sorts=order_items.total_sale_price desc 0&limit=500&column_limit=50&vis={"type":"looker_bar"}

    input: number of orders this years vs last year
    output:fields=order_items.count,order_items.created_year,order_items.created_month_name&pivots=order_items.created_year&f[order_items.created_year]=this year, last year&sorts=order_items.created_year desc,order_items.count desc 0&limit=5000&column_limit=50

    input : users by traffic source
    output:fields=users.traffic_source,users.count&sorts=users.count desc 0&limit=500

    input : customers who likes columbia or levi's
    output :fields=users.email,products.brand,order_items.total_sale_price&f[products.brand]=Columbia, Levi's&sorts=order_items.total_sale_price desc 0&limit=500

    input : Last week's revenue by category and department
    output :fields=products.category,products.department,order_items.total_sale_price&pivots=products.department&order_items.created_year&f[order_items.created_date]=last week&sorts=order_items.total_sale_price desc 0&limit=500&column_limit=50

    input : Sales performance by state, on a map
    output :fields=order_items.order_count,users.count,order_items.total_sale_price,order_items.average_spend_per_user,users.state&f[order_items.created_date]=90 days&sorts=order_items.total_sale_price desc&limit=500&column_limit=50&vis={"type" : "looker_google_map"}

    input : Who are the customer with highest revenue in New York?
    output :fields=users.email,user_order_facts.lifetime_revenue&f[users.state]=New York&sorts=user_order_facts.lifetime_revenue desc 0&limit=500=vis_config={"type" : "looker_grid"}

    input : Customers who made a purchase in last 6 month or acquired from facebook,
    output :fields=users.email&filter_expression=matches_filter(${order_items.created_date}, `6 months`) OR matches_filter(${users.traffic_source}, `Facebook`)

    input : Items in Pants or  part of first purchase order
    output :fields=products.item_name,order_items.count&filter_expression=matches_filter(${order_facts.is_first_purchase}, `Yes`) OR matches_filter(${products.category}, `Pants`)

    input : Customer who made last 6 month or acquired from facebook and purchased from brand Levi's
    output :fields=products.item_name,order_items.count&filter_expression=matches_filter(${order_items.created_date}, `6 months`) OR matches_filter(${users.traffic_source}, `Facebook`) AND matches_filter(${products.brand}, `Levi's`)

    """


    request_json = request.get_json(silent=True)
    request_args = request.args

    print("JSON: ", request.get_json(silent=True))

    

    if request_json and 'question' in request_json:
        llm = """
            input: {}
            output: """.format(request_json['question']) ### Formating our input to the model
        predict = context + request_json['explore'] + examples + llm

        model = ''

        # if the token limit exceeds what text-bison can handle, initialize the text-bison-32k model
        if(len(tokenizer(predict)) > 3000):
            print("Text Bison 32k. Token Count: ", len(tokenizer(predict)))
            from vertexai.preview.language_models import TextGenerationModel
            model = TextGenerationModel.from_pretrained("text-bison-32k")
        else:
            print("Text Bison. Token Count: ", len(tokenizer(predict)))
            from vertexai.language_models import TextGenerationModel
            model = TextGenerationModel.from_pretrained("text-bison")

        
        response =  model.predict(predict,**parameters).text # LLM Response

        # Set CORS headers for extension request
        headers = {
            "Access-Control-Allow-Origin": "*"
        }

        print("Response: ", response, "Headers: ", headers)

        return (response,200,headers)
    else:
        return ('Bad Request',400)