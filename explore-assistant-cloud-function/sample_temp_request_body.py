{
    "tool_name": "generate_explore_parameters",
    "arguments": {
        "prompt": "how were sales last year?",
        "conversation_id": "conversation_1754591905868_nng0gjm2q",
        "prompt_history": [
            "how were sales last year?"
        ],
        "thread_messages": [],
        "current_explore": {
            "exploreKey": "retail_data_sr:shoe_store_customers",
            "modelName": "retail_data_sr",
            "exploreId": "shoe_store_customers"
        },
        "golden_queries": {
            "exploreEntries": [
                {
                    "golden_queries.explore_id": "retail_data_sr:shoe_store_customers",
                    "golden_queries.input": "What are the predicted repeat purchase outcomes and probabilities for a sample of 500 customers, including their IDs and email addresses?",
                    "golden_queries.output": "{\"fields\": [\"[\\\"shoe_store_customers.customer_id\\\"\", \"\\\"shoe_store_customers.email_address\\\"\", \"\\\"predict_will_return.predicted_repeat_purchase_within_time\\\"\", \"\\\"predict_will_return.probability_of_repeat_purchase\\\"]\"], \"sorts\": [\"[\\\"shoe_store_customers.customer_id\\\"]\"], \"limit\": \"500\", \"model\": \"retail_data_sr\", \"view\": \"shoe_store_customers\"}",
                    "explore_assistant_refinement_examples.examples": null,
                    "explore_assistant_samples.samples": null
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "How has total ARR trended for Microsoft over the past 3 years",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.arr_quarter&fill_fields=vw_total_arr_ytd.arr_quarter&f[vw_total_arr_ytd.arr_quarter]=3+years&f[vw_total_arr_ytd.global_duns_name]=Microsoft+Corporation&sorts=vw_total_arr_ytd.arr_quarter+desc&limit=500&column_limit=50",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "What were the top 10 skus for Citrix in 2024",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.sku_description&f[vw_total_arr_ytd.product_level_1]=Citrix&f[vw_total_arr_ytd.arr_year]=2024&sorts=vw_total_arr_ytd.total_arr+desc&limit=10",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "Show me a list of accounts with at least $10 million dollars this quarter",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.global_duns_name&f[vw_total_arr_ytd.arr_year]=this+quarter&f[vw_total_arr_ytd.total_arr]=%3E10000000&sorts=vw_total_arr_ytd.total_arr+desc",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "What is the total ARR for vodafone for all future quarters?",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.arr_quarter]=after+today&f[vw_total_arr_ytd.global_duns_name]=VODAFONE+GROUP+PUBLIC+LIMITED+COMPANY&limit=500&column_limit=50",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "Show me a breakout of revenue by product this year",
                    "golden_queries.output": "fields=vw_total_arr_ytd.product_level_1,vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.product_level_1]=-NULL&f[vw_total_arr_ytd.arr_year]=this+year&sorts=vw_total_arr_ytd.product_level_1",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "Show me a trend of revenue for the last 8 quarters excluding citrix",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.arr_quarter&fill_fields=vw_total_arr_ytd.arr_quarter&f[vw_total_arr_ytd.arr_quarter]=8+quarters&f[vw_total_arr_ytd.product_level_1]=Citrix&sorts=vw_total_arr_ytd.arr_quarter+desc&limit=500&column_limit=50",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "What is the ARR for Walmart over the next year?",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.arr_quarter]=next++quarter+for+4+quarters&f[vw_total_arr_ytd.global_duns_name]=Walmart+Inc.&limit=500&column_limit=50",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "What is the all time ARR for AXA?",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.global_duns_name]=AXA&sorts=vw_total_arr_ytd.total_arr+desc+0&limit=500&column_limit=50&vis=\"type\":\"single_value\"",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "What is the ARR for Microsoft this quarter?",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.global_duns_name]=Microsoft+Corporation&f[vw_total_arr_ytd.arr_quarter]=this+quarter&limit=500&column_limit=50",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "How does quarterly revenue compare this year vs last year",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.arr_year,vw_total_arr_ytd.arr_quarter_of_year&pivots=vw_total_arr_ytd.arr_year&fill_fields=vw_total_arr_ytd.arr_quarter_of_year,vw_total_arr_ytd.arr_year&f[vw_total_arr_ytd.arr_year]=2+years&sorts=vw_total_arr_ytd.arr_year,vw_total_arr_ytd.arr_quarter_of_year,vw_total_arr_ytd.total_arr+desc+0",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "How does microsoft and oracle revenue compare this year",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.global_duns_name&f[vw_total_arr_ytd.arr_year]=this+year&f[vw_total_arr_ytd.global_duns_name]=Microsoft+Corporation%2COracle+Corporation&sorts=vw_total_arr_ytd.total_arr+desc",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "Show me a trend of ARR by contract end date in 2025",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.modified_contract_end_date&fill_fields=vw_total_arr_ytd.modified_contract_end_date&f[vw_total_arr_ytd.modified_contract_end_year]=2025&sorts=vw_total_arr_ytd.modified_contract_end_date+desc&limit=500&column_limit=50",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                },
                {
                    "golden_queries.explore_id": "sales_demo_the_look:order_items",
                    "golden_queries.input": "What is the ARR for Tibco this year across all accounts?",
                    "golden_queries.output": "fields=vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.arr_quarter]=this+year&f[vw_total_arr_ytd.product_level_1]=TIBCO&limit=500&column_limit=50",
                    "explore_assistant_refinement_examples.examples": "[{\"input\": [\"make a chart of sales by region\", \"make it a an area chart\", \"make it a table\"], \"output\": \"make a chart of sales by region make it a table\"}, {\"input\": [\"show me sales by region\", \"by product\"], \"output\": \"show me sales by region and product\"}]",
                    "explore_assistant_samples.samples": "[{\"category\": \"ARR Totals\", \"prompt\": \"What is the ARR for Microsoft this quarter??\"}, {\"category\": \"Product Breakouts\", \"prompt\": \"What is the trend in sales volume for blueberries over the last year?\"}]"
                }
            ],
            "exploreGenerationExamples": {
                "retail_data_sr:shoe_store_customers": [
                    {
                        "input": "What are the predicted repeat purchase outcomes and probabilities for a sample of 500 customers, including their IDs and email addresses?",
                        "output": "{\"fields\": [\"[\\\"shoe_store_customers.customer_id\\\"\", \"\\\"shoe_store_customers.email_address\\\"\", \"\\\"predict_will_return.predicted_repeat_purchase_within_time\\\"\", \"\\\"predict_will_return.probability_of_repeat_purchase\\\"]\"], \"sorts\": [\"[\\\"shoe_store_customers.customer_id\\\"]\"], \"limit\": \"500\", \"model\": \"retail_data_sr\", \"view\": \"shoe_store_customers\"}"
                    }
                ],
                "sales_demo_the_look:order_items": [
                    {
                        "input": "How has total ARR trended for Microsoft over the past 3 years",
                        "output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.arr_quarter&fill_fields=vw_total_arr_ytd.arr_quarter&f[vw_total_arr_ytd.arr_quarter]=3+years&f[vw_total_arr_ytd.global_duns_name]=Microsoft+Corporation&sorts=vw_total_arr_ytd.arr_quarter+desc&limit=500&column_limit=50"
                    },
                    {
                        "input": "What were the top 10 skus for Citrix in 2024",
                        "output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.sku_description&f[vw_total_arr_ytd.product_level_1]=Citrix&f[vw_total_arr_ytd.arr_year]=2024&sorts=vw_total_arr_ytd.total_arr+desc&limit=10"
                    },
                    {
                        "input": "Show me a list of accounts with at least $10 million dollars this quarter",
                        "output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.global_duns_name&f[vw_total_arr_ytd.arr_year]=this+quarter&f[vw_total_arr_ytd.total_arr]=%3E10000000&sorts=vw_total_arr_ytd.total_arr+desc"
                    },
                    {
                        "input": "What is the total ARR for vodafone for all future quarters?",
                        "output": "fields=vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.arr_quarter]=after+today&f[vw_total_arr_ytd.global_duns_name]=VODAFONE+GROUP+PUBLIC+LIMITED+COMPANY&limit=500&column_limit=50"
                    },
                    {
                        "input": "Show me a breakout of revenue by product this year",
                        "output": "fields=vw_total_arr_ytd.product_level_1,vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.product_level_1]=-NULL&f[vw_total_arr_ytd.arr_year]=this+year&sorts=vw_total_arr_ytd.product_level_1"
                    },
                    {
                        "input": "Show me a trend of revenue for the last 8 quarters excluding citrix",
                        "output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.arr_quarter&fill_fields=vw_total_arr_ytd.arr_quarter&f[vw_total_arr_ytd.arr_quarter]=8+quarters&f[vw_total_arr_ytd.product_level_1]=Citrix&sorts=vw_total_arr_ytd.arr_quarter+desc&limit=500&column_limit=50"
                    },
                    {
                        "input": "What is the ARR for Walmart over the next year?",
                        "output": "fields=vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.arr_quarter]=next++quarter+for+4+quarters&f[vw_total_arr_ytd.global_duns_name]=Walmart+Inc.&limit=500&column_limit=50"
                    },
                    {
                        "input": "What is the all time ARR for AXA?",
                        "output": "fields=vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.global_duns_name]=AXA&sorts=vw_total_arr_ytd.total_arr+desc+0&limit=500&column_limit=50&vis=\"type\":\"single_value\""
                    },
                    {
                        "input": "What is the ARR for Microsoft this quarter?",
                        "output": "fields=vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.global_duns_name]=Microsoft+Corporation&f[vw_total_arr_ytd.arr_quarter]=this+quarter&limit=500&column_limit=50"
                    },
                    {
                        "input": "How does quarterly revenue compare this year vs last year",
                        "output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.arr_year,vw_total_arr_ytd.arr_quarter_of_year&pivots=vw_total_arr_ytd.arr_year&fill_fields=vw_total_arr_ytd.arr_quarter_of_year,vw_total_arr_ytd.arr_year&f[vw_total_arr_ytd.arr_year]=2+years&sorts=vw_total_arr_ytd.arr_year,vw_total_arr_ytd.arr_quarter_of_year,vw_total_arr_ytd.total_arr+desc+0"
                    },
                    {
                        "input": "How does microsoft and oracle revenue compare this year",
                        "output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.global_duns_name&f[vw_total_arr_ytd.arr_year]=this+year&f[vw_total_arr_ytd.global_duns_name]=Microsoft+Corporation%2COracle+Corporation&sorts=vw_total_arr_ytd.total_arr+desc"
                    },
                    {
                        "input": "Show me a trend of ARR by contract end date in 2025",
                        "output": "fields=vw_total_arr_ytd.total_arr,vw_total_arr_ytd.modified_contract_end_date&fill_fields=vw_total_arr_ytd.modified_contract_end_date&f[vw_total_arr_ytd.modified_contract_end_year]=2025&sorts=vw_total_arr_ytd.modified_contract_end_date+desc&limit=500&column_limit=50"
                    },
                    {
                        "input": "What is the ARR for Tibco this year across all accounts?",
                        "output": "fields=vw_total_arr_ytd.total_arr&f[vw_total_arr_ytd.arr_quarter]=this+year&f[vw_total_arr_ytd.product_level_1]=TIBCO&limit=500&column_limit=50"
                    }
                ]
            },
            "exploreRefinementExamples": {
                "retail_data_sr:shoe_store_customers": [],
                "sales_demo_the_look:order_items": [
                    {
                        "input": [
                            "make a chart of sales by region",
                            "make it a an area chart",
                            "make it a table"
                        ],
                        "output": "make a chart of sales by region make it a table"
                    },
                    {
                        "input": [
                            "show me sales by region",
                            "by product"
                        ],
                        "output": "show me sales by region and product"
                    }
                ]
            },
            "exploreSamples": {
                "retail_data_sr:shoe_store_customers": [],
                "sales_demo_the_look:order_items": [
                    {
                        "category": "ARR Totals",
                        "prompt": "What is the ARR for Microsoft this quarter??"
                    },
                    {
                        "category": "Product Breakouts",
                        "prompt": "What is the trend in sales volume for blueberries over the last year?"
                    }
                ]
            }
        },
        "semantic_models": {
            "retail_data_sr:shoe_store_customers": {
                "exploreId": "shoe_store_customers",
                "modelName": "retail_data_sr",
                "exploreKey": "retail_data_sr:shoe_store_customers",
                "dimensions": [
                    {
                        "name": "customer_stats.zipcode",
                        "type": "zipcode",
                        "label": "Customer Stats Customer Zipcode",
                        "description": "Lists all customer zipcodes",
                        "tags": []
                    },
                    {
                        "name": "customer_stats.first_trans_date",
                        "type": "number",
                        "label": "Customer Stats First Transaction Date",
                        "description": "The customers first transaction date",
                        "tags": []
                    },
                    {
                        "name": "customer_stats.last_trans_date",
                        "type": "number",
                        "label": "Customer Stats Last Transaction Date",
                        "description": "The customers last transaction date",
                        "tags": []
                    },
                    {
                        "name": "customer_stats.avg_discount",
                        "type": "number",
                        "label": "Customer Stats Lifetime Average Discount",
                        "description": "The average discount a customer has through customer lifetime",
                        "tags": []
                    },
                    {
                        "name": "customer_stats.count_giftcards",
                        "type": "number",
                        "label": "Customer Stats Lifetime Giftcards Used",
                        "description": "Lists the number of giftcards used by a customer",
                        "tags": []
                    },
                    {
                        "name": "customer_stats.count_items",
                        "type": "number",
                        "label": "Customer Stats Lifetime Items Purchased",
                        "description": "Lists the number of items purchased by a customer",
                        "tags": []
                    },
                    {
                        "name": "customer_stats.total_extended_retail",
                        "type": "number",
                        "label": "Customer Stats Lifetime Spend",
                        "description": "Lists the ",
                        "tags": []
                    },
                    {
                        "name": "customer_stats.count_distinct_stores",
                        "type": "number",
                        "label": "Customer Stats Lifetime Stores Visted",
                        "description": "Lists the number of stores visted by a customer",
                        "tags": []
                    },
                    {
                        "name": "customer_stats.count_tickets",
                        "type": "number",
                        "label": "Customer Stats Lifetime Tickets",
                        "description": "Lists the number of tickets by a customer",
                        "tags": []
                    },
                    {
                        "name": "customer_stats.multi_store_customer",
                        "type": "yesno",
                        "label": "Customer Stats Multi Store Customer (Yes / No)",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "customer_stats.repeating_customer",
                        "type": "yesno",
                        "label": "Customer Stats Repeating Customer (Yes / No)",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.customer_id",
                        "type": "number",
                        "label": "Predict Will Return Customer ID",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.department_categories",
                        "type": "string",
                        "label": "Predict Will Return Department Categories",
                        "description": "The category the customer spent the most money during thier first purchase",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.department_demographics",
                        "type": "string",
                        "label": "Predict Will Return Department Demographics",
                        "description": "The demographic the customer spent the most money during thier first purchase",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.discount_level",
                        "type": "string",
                        "label": "Predict Will Return Discount Level",
                        "description": "The discount level recieved on the customers first purchase",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.is_local",
                        "type": "string",
                        "label": "Predict Will Return Is Local",
                        "description": "Whether the customer is or isn't local to the 2 main stores, or unknown if the customer doesn't have a zipcode record.",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.item_segments",
                        "type": "string",
                        "label": "Predict Will Return Item Segments",
                        "description": "The amount of items purchased during their first purchase",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.primary_store_name",
                        "type": "string",
                        "label": "Predict Will Return Primary Store Name",
                        "description": "The store the customer shopped in during thier first purchase",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.repeat_purchase_within_time",
                        "type": "string",
                        "label": "Predict Will Return Repeat Purchase Within Time",
                        "description": "Whether the customer returned within 180 days of thier first purchase",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.revenue_buckets",
                        "type": "string",
                        "label": "Predict Will Return Revenue Buckets",
                        "description": "The amount of money spent during their first purchase",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.probability_of_no_repeat_purchase",
                        "type": "number",
                        "label": "Predict Will Return Will Not Return Probability",
                        "description": "The predicted probability of a customer not returning",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.predicted_repeat_purchase_within_time",
                        "type": "string",
                        "label": "Predict Will Return Will Return Prediction Yes/No",
                        "description": "The prediction the model has on whether the customer will vs. will not return",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.probability_of_repeat_purchase",
                        "type": "number",
                        "label": "Predict Will Return Will Return Probability",
                        "description": "The predicted probability of a customer returning",
                        "tags": []
                    },
                    {
                        "name": "shoe_store_customers.email_address",
                        "type": "string",
                        "label": "Store Customers Customer Email Address",
                        "description": "Lists all customer email address",
                        "tags": []
                    },
                    {
                        "name": "shoe_store_customers.customer_id",
                        "type": "number",
                        "label": "Store Customers Customer ID",
                        "description": "Uniquely identifies a customer",
                        "tags": []
                    },
                    {
                        "name": "shoe_store_customers.customer_fullname",
                        "type": "string",
                        "label": "Store Customers Customer's Fullname",
                        "description": "List all customer fullnames",
                        "tags": []
                    }
                ],
                "measures": [
                    {
                        "name": "predict_will_return.count_customers",
                        "type": "count",
                        "label": "Predict Will Return Count Customers",
                        "description": "Counts all customers",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.count_of_not_repeat_purchasers",
                        "type": "count",
                        "label": "Predict Will Return Count Customers Predicted to Not Return",
                        "description": "Counts the customers the model predicted to not return",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.count_of_repeat_purchasers",
                        "type": "count",
                        "label": "Predict Will Return Count Customers Predicted to Return",
                        "description": "Counts the customers the model predicted to return",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.count_returned_customers",
                        "type": "count",
                        "label": "Predict Will Return Count Returned Customers",
                        "description": "Counts customers who have already returned to the store",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.count_false_negative",
                        "type": "count",
                        "label": "Predict Will Return Count customers predicted NOT to return and did return (False Negative)",
                        "description": "Customers who were predicted to NOT return, and have returned.",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.count_true_negative",
                        "type": "count",
                        "label": "Predict Will Return Count customers predicted NOT to return and haven't returned yet (True Negative)",
                        "description": "Customers who were predicted to NOT return, and haven't returned yet.",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.count_true_positive",
                        "type": "count",
                        "label": "Predict Will Return Count customers predicted to return and did return (True Positive)",
                        "description": "Customers who were predicted to return and have already returned",
                        "tags": []
                    },
                    {
                        "name": "predict_will_return.count_false_positive",
                        "type": "count",
                        "label": "Predict Will Return Count customers predicted to return and haven't returned yet (False Positive)",
                        "description": "Customers who haven't returned yet, but still have time to return",
                        "tags": []
                    },
                    {
                        "name": "shoe_store_customers.count_customers",
                        "type": "count",
                        "label": "Store Customers Count Customers",
                        "description": "Counts the number of customers",
                        "tags": []
                    }
                ],
                "description": ""
            },
            "sales_demo_the_look:order_items": {
                "exploreId": "order_items",
                "modelName": "sales_demo_the_look",
                "exploreKey": "sales_demo_the_look:order_items",
                "dimensions": [
                    {
                        "name": "distribution_centers.name",
                        "type": "string",
                        "label": "Distribution Centers Distribution Center",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "distribution_centers.latitude",
                        "type": "number",
                        "label": "Distribution Centers Latitude",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "distribution_centers.location",
                        "type": "location",
                        "label": "Distribution Centers Location",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "distribution_centers.longitude",
                        "type": "number",
                        "label": "Distribution Centers Longitude",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.created_date",
                        "type": "date_date",
                        "label": "Inventory Items Created Date",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.created_month",
                        "type": "date_month",
                        "label": "Inventory Items Created Month",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.created_quarter",
                        "type": "date_quarter",
                        "label": "Inventory Items Created Quarter",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.created_time",
                        "type": "date_time",
                        "label": "Inventory Items Created Time",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.created_week",
                        "type": "date_week",
                        "label": "Inventory Items Created Week",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.created_year",
                        "type": "date_year",
                        "label": "Inventory Items Created Year",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.sold_date",
                        "type": "date_date",
                        "label": "Inventory Items Sold Date",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.sold_month",
                        "type": "date_month",
                        "label": "Inventory Items Sold Month",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.sold_quarter",
                        "type": "date_quarter",
                        "label": "Inventory Items Sold Quarter",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.sold_time",
                        "type": "date_time",
                        "label": "Inventory Items Sold Time",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.sold_week",
                        "type": "date_week",
                        "label": "Inventory Items Sold Week",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "inventory_items.sold_year",
                        "type": "date_year",
                        "label": "Inventory Items Sold Year",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.created_date",
                        "type": "date_date",
                        "label": "Order Items Created Date",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.created_day_of_year",
                        "type": "date_day_of_year",
                        "label": "Order Items Created Day of Year",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.created_hour",
                        "type": "date_hour",
                        "label": "Order Items Created Hour",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.created_month",
                        "type": "date_month",
                        "label": "Order Items Created Month",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.created_month_name",
                        "type": "date_month_name",
                        "label": "Order Items Created Month Name",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.created_quarter",
                        "type": "date_quarter",
                        "label": "Order Items Created Quarter",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.created_time",
                        "type": "date_time",
                        "label": "Order Items Created Time",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.created_week",
                        "type": "date_week",
                        "label": "Order Items Created Week",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.created_year",
                        "type": "date_year",
                        "label": "Order Items Created Year",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "orders.days_datediff_returned",
                        "type": "duration_day",
                        "label": "Order Items Days Datediff Returned",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.delivered_date",
                        "type": "date_date",
                        "label": "Order Items Delivered Date",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.delivered_month",
                        "type": "date_month",
                        "label": "Order Items Delivered Month",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.delivered_quarter",
                        "type": "date_quarter",
                        "label": "Order Items Delivered Quarter",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.delivered_time",
                        "type": "date_time",
                        "label": "Order Items Delivered Time",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.delivered_week",
                        "type": "date_week",
                        "label": "Order Items Delivered Week",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.delivered_year",
                        "type": "date_year",
                        "label": "Order Items Delivered Year",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.failure_percentage_unrecoverable_cost_value",
                        "type": "number",
                        "label": "Order Items Failure Percentage Unrecoverable Cost Value",
                        "description": "Value of the parameter Failure Unrecoverable Cost",
                        "tags": []
                    },
                    {
                        "name": "orders.hours_datediff_returned",
                        "type": "duration_hour",
                        "label": "Order Items Hours Datediff Returned",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.is_product_returned",
                        "type": "yesno",
                        "label": "Order Items Is Product Returned (Yes / No)",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "orders.minutes_datediff_returned",
                        "type": "duration_minute",
                        "label": "Order Items Minutes Datediff Returned",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "orders.months_datediff_returned",
                        "type": "duration_month",
                        "label": "Order Items Months Datediff Returned",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.order_id",
                        "type": "string",
                        "label": "Order Items Order ID",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "orders.quarters_datediff_returned",
                        "type": "duration_quarter",
                        "label": "Order Items Quarters Datediff Returned",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.reporting_period",
                        "type": "string",
                        "label": "Order Items Reporting Period",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.returned_date",
                        "type": "date_date",
                        "label": "Order Items Returned Date",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.returned_month",
                        "type": "date_month",
                        "label": "Order Items Returned Month",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.returned_quarter",
                        "type": "date_quarter",
                        "label": "Order Items Returned Quarter",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.returned_time",
                        "type": "date_time",
                        "label": "Order Items Returned Time",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.returned_week",
                        "type": "date_week",
                        "label": "Order Items Returned Week",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.returned_year",
                        "type": "date_year",
                        "label": "Order Items Returned Year",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.sale_price",
                        "type": "number",
                        "label": "Order Items Sale Price",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.sale_price_bin",
                        "type": "tier",
                        "label": "Order Items Sale Price Bin",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "orders.seconds_datediff_returned",
                        "type": "duration_second",
                        "label": "Order Items Seconds Datediff Returned",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.shipped_date",
                        "type": "date_date",
                        "label": "Order Items Shipped Date",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.shipped_month",
                        "type": "date_month",
                        "label": "Order Items Shipped Month",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.shipped_quarter",
                        "type": "date_quarter",
                        "label": "Order Items Shipped Quarter",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.shipped_time",
                        "type": "date_time",
                        "label": "Order Items Shipped Time",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.shipped_week",
                        "type": "date_week",
                        "label": "Order Items Shipped Week",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.shipped_year",
                        "type": "date_year",
                        "label": "Order Items Shipped Year",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.status",
                        "type": "string",
                        "label": "Order Items Status",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "orders.weeks_datediff_returned",
                        "type": "duration_week",
                        "label": "Order Items Weeks Datediff Returned",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "orders.years_datediff_returned",
                        "type": "duration_year",
                        "label": "Order Items Years Datediff Returned",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.brand",
                        "type": "string",
                        "label": "Products Brand",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.category",
                        "type": "string",
                        "label": "Products Category",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.department",
                        "type": "string",
                        "label": "Products Department",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.distribution_center_id",
                        "type": "number",
                        "label": "Products Distribution Center ID",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.name",
                        "type": "string",
                        "label": "Products Name",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.retail_price",
                        "type": "number",
                        "label": "Products Retail Price",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.sku",
                        "type": "string",
                        "label": "Products SKU",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "repeat_purchases.days_between_orders",
                        "type": "number",
                        "label": "Repeat Purchases Days Between Orders",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "repeat_purchases.is_repeat_purchase_within_30_days",
                        "type": "yesno",
                        "label": "Repeat Purchases Is Repeat Purchase Within 30 Days (Yes / No)",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "repeat_purchases.order_sequence_number",
                        "type": "number",
                        "label": "Repeat Purchases Order Sequence Number",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "repeat_purchases.user_id",
                        "type": "number",
                        "label": "Repeat Purchases User ID",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.age",
                        "type": "number",
                        "label": "Users Age",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.age_buckets",
                        "type": "tier",
                        "label": "Users Age Buckets",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.approx_latitude",
                        "type": "number",
                        "label": "Users Approx Latitude",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.approx_longitude",
                        "type": "number",
                        "label": "Users Approx Longitude",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.city",
                        "type": "string",
                        "label": "Users City",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.country",
                        "type": "string",
                        "label": "Users Country",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.created_date",
                        "type": "date_date",
                        "label": "Users Created Date",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.created_month",
                        "type": "date_month",
                        "label": "Users Created Month",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.created_quarter",
                        "type": "date_quarter",
                        "label": "Users Created Quarter",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.created_time",
                        "type": "date_time",
                        "label": "Users Created Time",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.created_week",
                        "type": "date_week",
                        "label": "Users Created Week",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.created_year",
                        "type": "date_year",
                        "label": "Users Created Year",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.email",
                        "type": "string",
                        "label": "Users Email",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.first_name",
                        "type": "string",
                        "label": "Users First Name",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.full_name",
                        "type": "string",
                        "label": "Users Full Name",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.gender",
                        "type": "string",
                        "label": "Users Gender",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.id",
                        "type": "string",
                        "label": "Users ID",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.last_name",
                        "type": "string",
                        "label": "Users Last Name",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.latitude",
                        "type": "number",
                        "label": "Users Latitude",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.longitude",
                        "type": "number",
                        "label": "Users Longitude",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.postal_code",
                        "type": "string",
                        "label": "Users Postal Code",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.state",
                        "type": "string",
                        "label": "Users State",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.street_address",
                        "type": "string",
                        "label": "Users Street Address",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.traffic_source",
                        "type": "string",
                        "label": "Users Traffic Source",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.user_location",
                        "type": "location",
                        "label": "Users User Location",
                        "description": "",
                        "tags": []
                    }
                ],
                "measures": [
                    {
                        "name": "inventory_items.number_of_inventory_items",
                        "type": "count_distinct",
                        "label": "Inventory Items Number of Inventory Items",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.average_sale_price",
                        "type": "average",
                        "label": "Order Items Average Sale Price",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.percentage_defective_production",
                        "type": "number",
                        "label": "Order Items Defective Production %",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.number_of_order_items",
                        "type": "count",
                        "label": "Order Items Number of Order Items",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.number_of_order_items_last_week",
                        "type": "count",
                        "label": "Order Items Number of Order Items Last Week",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.number_of_order_items_this_week",
                        "type": "count",
                        "label": "Order Items Number of Order Items This Week",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "orders.number_of_orders",
                        "type": "count_distinct",
                        "label": "Order Items Number of Orders",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.number_of_returned_items",
                        "type": "count",
                        "label": "Order Items Number of Returned Items",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.total_sale_price",
                        "type": "sum",
                        "label": "Order Items Total Sale Price",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "order_items.unrecoverable_failure_cost",
                        "type": "sum",
                        "label": "Order Items Unrecoverable Failure Cost",
                        "description": "cost associated with defected items",
                        "tags": []
                    },
                    {
                        "name": "products.average_cost",
                        "type": "average_distinct",
                        "label": "Products Average Cost",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.average_retail_price",
                        "type": "average_distinct",
                        "label": "Products Average Retail Price",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.gross_margin",
                        "type": "number",
                        "label": "Products Gross Margin",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.gross_margin_percentange",
                        "type": "number",
                        "label": "Products Gross Margin %",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.test",
                        "type": "count_distinct",
                        "label": "Products Test",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.total_cost",
                        "type": "sum_distinct",
                        "label": "Products Total Cost",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "products.total_retail_price",
                        "type": "sum_distinct",
                        "label": "Products Total Retail Price",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "repeat_purchases.number_of_repeat_purchases",
                        "type": "count_distinct",
                        "label": "Repeat Purchases Number of Repeat Purchases",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "repeat_purchases.number_of_repeat_purchases_within_30",
                        "type": "count_distinct",
                        "label": "Repeat Purchases Number of Repeat Purchases Within 30",
                        "description": "number of repeat purchases within 30 days",
                        "tags": []
                    },
                    {
                        "name": "repeat_purchases.percentage_repeat_purchase",
                        "type": "number",
                        "label": "Repeat Purchases Repeat Purchase Rate",
                        "description": "percentage of repeat purchases within 30 days",
                        "tags": []
                    },
                    {
                        "name": "x_repeat_purchases_orders.percentage_repeat_purchase",
                        "type": "number",
                        "label": "Repeat Purchases Repeat Purchase Rate",
                        "description": "percentage of repeat purchases within 30 days",
                        "tags": []
                    },
                    {
                        "name": "users.average_age",
                        "type": "average_distinct",
                        "label": "Users Average Age",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "x_orders_users.average_spend_per_user",
                        "type": "number",
                        "label": "Users Average Spend per User",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.number_of_facebook_users_over_65",
                        "type": "count_distinct",
                        "label": "Users Number of Facebook Users Over 65",
                        "description": "",
                        "tags": []
                    },
                    {
                        "name": "users.number_of_users",
                        "type": "count_distinct",
                        "label": "Users Number of Users",
                        "description": "",
                        "tags": []
                    }
                ],
                "description": ""
            }
        },
        "model_name": "",
        "vertex_model": "gemini-2.0-flash",
        "test_mode": false,
        "selected_area": "Sales & Revenue",
        "restricted_explore_keys": [
            "sales_demo_the_look:order_items"
        ]
    }
}