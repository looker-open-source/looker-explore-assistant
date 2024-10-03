import looker_sdk
import vertexai
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from looker_sdk import models40 as models, error
import configparser
import json
import urllib.parse
import re
import argparse
import os
import subprocess

# Function to call load_examples.py
def load_examples(project_id, dataset_id, table_id, column_name, explore_id, json_file):
    command = [
        "python", "load_examples.py",
        "--project_id", project_id,
        "--dataset_id", dataset_id,
        "--table_id", table_id,
        "--column_name", column_name,
        "--explore_id", explore_id,
        "--json_file", json_file
    ]
    subprocess.run(command)


# Initialize Looker SDK using environment variables
def init_looker_sdk():
    # Ensure the required environment variables are set
    required_env_vars = ["LOOKERSDK_BASE_URL", "LOOKERSDK_CLIENT_ID", "LOOKERSDK_CLIENT_SECRET"]
    for var in required_env_vars:
        if not os.getenv(var):
            raise EnvironmentError(f"Environment variable {var} is not set")

    # Initialize the SDK using environment variables
    return looker_sdk.init40()
    
# Fetch Explore Metadata
def fetch_explore_metadata(sdk, model, explore, fields):
    data = sdk.lookml_model_explore(model, explore, fields)

    # Dimensions
    dimensions = []
    for field in data.fields.dimensions:
        dimensions.append(f"name: {field.name}, type: {field.type}, description: {field.description} \n")

    # Measures
    measures = []
    for field in data.fields.measures:
        measures.append(f"name: {field.name}, type: {field.type}, description: {field.description} \n")

    return {
        "dimensions": dimensions,
        "measures": measures
    }

# Format Explore Metadata
def format_explore_metadata(data):
    return f"""
    Dimensions Used to group by information:\n {''.join(data['dimensions'])}
    Measures are used to perform calculations/aggregations (if top, bottom, total, sum, etc. are used include a measure):\n {''.join(data['measures'])}
    """

# Fetch Query URL Metadata
def fetch_query_url_metadata(sdk, explore):
    try:
        response = sdk.run_inline_query(
            result_format='json',
            cache=True,
            body=models.WriteQuery(
                model="system__activity",
                view="history",
                fields=[
                    "query.slug",
                    "query.view",
                    "query.dynamic_fields",
                    "query.formatted_fields",
                    "query.filters",
                    "query.filter_expression",
                    "query.formatted_pivots",
                    "query.sorts",
                    "query.limit",
                    "query.column_limit",
                    "query.count"
                ],
                filters={
                    "query.view": explore,
                    "history.status": "complete",
                },
                sorts=[
                    "history.completed_time desc",
                    "query.view"
                ],
                limit="10",
            )
        )
        return json.loads(response)[0:10]
    except error.SDKError as e:
        print(e.message)
        return []

# Fetch Query URL
def fetch_query_url(sdk, slug):
    try:
        query_url = sdk.query_for_slug(slug=slug)
        return query_url
    except error.SDKError as e:
        print(e.message)
        return None


### LOOKER URL PARSER FUNCTIONS

# limit categorization
def limit_categorization(query,url, categorized_queries):
  if "query.limit" in query and query['query.limit'] != None:
      categorized_queries.setdefault('limit',[])
      categorized_queries['limit'].append(url)

# dynamic fields categorization
def dynamic_fields_categorization(query,url, categorized_queries):
  if "query.dynamic_fields" in query and query['query.dynamic_fields'] != None:
      categorized_queries.setdefault('dynamic_fields',[])
      categorized_queries['dynamic_fields'].append(url)

# sorts categorization
def sorts_categorization(query,url, categorized_queries):
  if "query.sorts" in query and query['query.sorts'] != None:
      categorized_queries.setdefault('sorts',[])
      categorized_queries['sorts'].append(url)

# filter expression categorization
def filter_expression_categorization(query,url, categorized_queries):
  if "query.filter_expression" in query and query['query.filter_expression'] != None:
      categorized_queries.setdefault('filter_expression',[])
      categorized_queries['filter_expression'].append(url)

# pivots categorization
def pivots_categorization(query,url, categorized_queries):
  if "query.formatted_pivots" in query and query['query.formatted_pivots'] != None:
      categorized_queries.setdefault('pivots',[])
      categorized_queries['pivots'].append(url)

# filters categorization
def filters_categorization(query,url, categorized_queries):
    # Time / Date Regex Patterns
    time_relative_pattern = r"(\d+)\s+(month|week|day|year)?(?:\s+ago)?"
    time_range_pattern = r"\b(\d+)\s+(month|week|day|year)s?\s+ago\s+for\s+\1\s+\2\b"

    # Numerical Patterns
    numerical_comparison_pattern = r"^(>|>=|<|<=|<>)?(\d+)$"
    numerical_range_pattern = r"\b(>|>=|<|<=|<>)?(\d+)?\s+(AND|OR)?\s+(>|>=|<|<=|<>)?(\d+)"

    # String Patterns
    string_catch_all_pattern = r"\w"
    string_multiple_pattern = r"\w,+\w"
    categorized_queries_filters = {}

    parsed_filters = json.loads(query['query.filters'])
    keys_copy = tuple(parsed_filters.keys())
    for key in keys_copy:
      if parsed_filters[key] != "":
        if re.findall(time_range_pattern, parsed_filters[key]):
            categorized_queries_filters.setdefault('time_range',[])
            categorized_queries_filters['time_range'].append(url)
            continue
        if re.findall(time_relative_pattern, parsed_filters[key]):
            categorized_queries_filters.setdefault('time_relative',[])
            categorized_queries_filters['time_relative'].append(url)
            continue
        elif re.findall(numerical_comparison_pattern, parsed_filters[key]):
            categorized_queries_filters.setdefault('numerical_comparison',[])
            categorized_queries_filters['numerical_comparison'].append(url)
            continue
        elif re.findall(numerical_range_pattern, parsed_filters[key]):
            categorized_queries_filters.setdefault('numerical_range',[])
            categorized_queries_filters['numerical_range'].append(url)
            continue
        elif re.findall(string_multiple_pattern, parsed_filters[key]):
            categorized_queries_filters.setdefault('string_multiple',[])
            categorized_queries_filters['string_multiple'].append(url)
            continue
        elif re.findall(r"\w",parsed_filters[key]):
            categorized_queries_filters.setdefault('string_standard',[])
            categorized_queries_filters['string_standard'].append(url)
            continue

### END


# Categorize URLs
def categorize_urls(data, sdk):
    categorized_queries = {}
    categorized_queries_filters = {}

    if not data:
        return categorized_queries

    for query in data:
        query_data = fetch_query_url(sdk, str(query['query.slug']))
        if not query_data:
            continue

        decoded_url = urllib.parse.unquote(query_data.url)
        url_parameters = decoded_url.split("?", 1)[1].replace("+", " ")
        decoded_url_notimezone = re.sub(r"&query_timezone=(.)*&", "&", url_parameters, count=1)
        decoded_url_nofilterconfig = re.sub(r"&filter_config=(.)*(?=&|$)", "&", decoded_url_notimezone)[0:-1] if re.sub(r"&filter_config=(.)*(?=&|$)", "&", decoded_url_notimezone)[-1] == "&" else re.sub(r"&filter_config=(.)*(?=&|$)", "&", decoded_url_notimezone)
        vis_config = re.search(r"(&vis=(.)*(?=&|$))", decoded_url_nofilterconfig)
        decoded_url_modifiedvisjson = ''
        if vis_config:
            vis_json_str = vis_config.group(1)
            vis_type = re.search(r'("type":\s*"([^,}]+))', vis_json_str)
            decoded_url_modifiedvisjson = re.sub(r"(&vis=(.)*(?=&|$))", "&vis={" + (vis_type.group(1) if vis_type else '') + "}", decoded_url_nofilterconfig)
        else:
            decoded_url_modifiedvisjson = decoded_url_nofilterconfig

        limit_categorization(query, decoded_url_modifiedvisjson, categorized_queries)
        dynamic_fields_categorization(query, decoded_url_modifiedvisjson, categorized_queries)
        sorts_categorization(query, decoded_url_modifiedvisjson, categorized_queries)
        filter_expression_categorization(query, decoded_url_modifiedvisjson, categorized_queries)
        pivots_categorization(query, decoded_url_modifiedvisjson, categorized_queries)
        filters_categorization(query, decoded_url_modifiedvisjson, categorized_queries_filters)

    categorized_queries['filters'] = categorized_queries_filters
    return categorized_queries

# Generate Input for Vertex AI
def generate_input(request):
    prompt_prefix = '''You are a specialized assistant that translates Looker Explore query URL's into natural language questions. By reading the different parameters of the url (like the fields used, filters, etc.) you are able to generate a natural language question.
        Please do not use the example fields such as 'user_order_facts', instead use fields relvant to the fields in the "output".
        That means if the "output" provided has no 'user_order_facts', don't return a question about users or orders, but instead return a result relevant to the types of fields in the output.
        Please keep the "input" short and concise using 1-2 sentences max in your repsonse. Make sure to generate a response that sounds like it's coming from an average person and not a data analyst who is very familiar with the data. Each request will contain an "input" and an "output" field. The "output" field will be the Looker Explore query url. The "input" field will be the natural language question that you will fill in/generate.
        Here is an example of a properly formatted response:
        {"input": "customer with lifetime revenue > 100", "output": "fields=user_order_facts.lifetime_revenue&f[user_order_facts.lifetime_revenue]=>100&sorts=user_order_facts.lifetime_revenue desc 0&limit=500"}
        Please alwasy respond with a only a json object with the fields 'input' and 'output', as you see above. Please do not respond in markup or using markup tags like ```. Here is an output that needs a matching input response you generate: '''
    model = GenerativeModel("gemini-pro")
    response = model.generate_content(
        contents=prompt_prefix + request,
        generation_config=GenerationConfig(
            temperature=0.2,
            top_p=0.8,
            top_k=40,
            max_output_tokens=1000,
            candidate_count=1
        )
    )
    return response.text

# Create categorized input queries
def generate_input_examples(sdk, model, explore):
    url_prompts = []

    data = fetch_query_url_metadata(sdk, explore)
    categorized_queries = categorize_urls(data, sdk)
    for key in categorized_queries.keys():
        if isinstance(categorized_queries[key], list):
            for url in categorized_queries[key][0:3]:
                response = generate_input(json.dumps({"input": "", "output": url}))
                # Remove ```json and ``` symbols
                cleaned_response = re.sub(r'```json\n|```', '', response).strip()
                if cleaned_response:
                    try:
                        url_prompts.append(json.loads(cleaned_response))
                    except json.JSONDecodeError as e:
                        print(f"Failed to decode JSON: {e}")
                        print(f"Response: {cleaned_response}")
                else:
                    print("Empty response received from generate_input")
        else:
            for key2 in categorized_queries[key].keys():
                for url in categorized_queries[key][key2][0:3]:
                    response = generate_input(json.dumps({"input": "", "output": url}))
                    # Remove ```json and ``` symbols
                    cleaned_response = re.sub(r'```json\n|```', '', response).strip()
                    if cleaned_response:
                        try:
                            url_prompts.append(json.loads(cleaned_response))
                        except json.JSONDecodeError as e:
                            print(f"Failed to decode JSON: {e}")
                            print(f"Response: {cleaned_response}")
                    else:
                        print("Empty response received from generate_input")

    # Write the JSON objects to the file as a list
    with open(f"./generated_examples/{model}:{explore}.inputs.txt", "w") as f:
        json.dump(url_prompts, f, indent=4)

# Main function to create example files
def create_example_files(model, explore, project_id, location, chain_load):
    sdk = init_looker_sdk()

    # Fetch Explore Metadata into files
    data = fetch_explore_metadata(sdk, model, explore, 'fields')
    with open(f"./generated_examples/{model}:{explore}.txt", "w") as f:
        f.write(format_explore_metadata(data))
    
    # Describe top queries for the explore and store in files
    vertexai.init(project=project_id, location=location)
    generate_input_examples(sdk, model, explore)


    # Optionally call load_examples.py
    if chain_load:
        json_file = f"./generated_examples/{model}:{explore}.inputs.txt"
        load_examples(project_id, "explore_assistant", "explore_assistant_examples", "examples", f"{model}:{explore}", json_file)

# Command-line argument parsing
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate example files for a given explore.")
    parser.add_argument("--model", required=True, help="Looker model name.")
    parser.add_argument("--explore", required=True, help="Looker explore name.")
    parser.add_argument("--project_id", required=True, help="Google Cloud project ID")
    parser.add_argument("--location", required=True, help="Google Cloud location")
    parser.add_argument("--chain_load", action="store_true", help="Load examples into BigQuery after generating them")
    args = parser.parse_args()

    create_example_files(args.model, args.explore, args.project_id, args.location, args.chain_load)  