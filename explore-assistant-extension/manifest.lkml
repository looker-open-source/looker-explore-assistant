application: explore_assistant {
    label: "Explore Assistant"
    url: "https://localhost:8080/bundle.js"
    file: "bundle.js"
    entitlements: {
      local_storage: yes
      navigation: yes
      new_window: yes
      new_window_external_urls: ["https://developers.generativeai.google/*"]
      use_form_submit: no
      use_embeds: yes
      use_iframes: yes
      use_clipboard: no
      core_api_methods: ["lookml_model_explore", "run_inline_query", "run_query", "create_query", "update_user_attribute", "create_user_attribute", "all_user_attributes", "me", "user_attribute_user_values", "search_roles", "login_user", "all_connections", "connection", "test_connection"]
      external_api_urls: ["https://us-central1-explore-assistant-test.cloudfunctions.net/explore-assistant-api", "https://www.googleapis.com", "https://us-central1-aiplatform.googleapis.com", "https://geminidataanalytics.googleapis.com", "https://localhost:8080", "http://localhost:8000/mcp/conversational-analytics", "http://localhost:8001", "https://looker-explore-assistant-mcp-rchq2jmtba-uc.a.run.app", "https://looker-explore-assistant-mcp-730192175971.us-central1.run.app"]
      oauth2_urls: ["https://accounts.google.com/o/oauth2/v2/auth"]
    }
}
