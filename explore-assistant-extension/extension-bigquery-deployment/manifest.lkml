project_name: "YOUR LOOKML PROJECT NAME"
application: explore-assistant {
label: "Explore Assistant"
file: "bundle.js"
# url: "https://localhost:8000/bundle.js"
entitlements: {
    core_api_methods: ["lookml_model_explore","run_inline_query","create_sql_query","run_sql_query"]
    navigation: yes
    use_embeds: yes
    use_iframes: yes
    new_window: yes
    new_window_external_urls: ["https://developers.generativeai.google/*"]
    local_storage: yes
}}
