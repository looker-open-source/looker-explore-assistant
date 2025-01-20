application: explore_assistant2 {
  label: "Beck's Explore Assistant"
  url: "https://localhost:8080/bundle.js"
  # file: "bundle.js"
  entitlements: {
    navigation: yes
    use_embeds: yes
    use_iframes: yes
    new_window: yes
    new_window_external_urls: ["https://developers.generativeai.google/*",
      "https://accounts.google.com/o/oauth2/v2/auth", "https://github.com/login/oauth/authorize", "https://dev-5eqts7im.auth0.com/authorize", "https://dev-5eqts7im.auth0.com/login/oauth/token", "https://github.com/login/oauth/access_token"
    ]
    local_storage: yes
    core_api_methods: ["me","lookml_model_explore","create_sql_query","run_sql_query","run_query","create_query"]
    external_api_urls: ["https://accounts.google.com/gsi/client",
      "https://accounts.google.com/o/oauth2/auth",
      "https://accounts.google.com/o/oauth2/token",
      "http://127.0.0.1:3000", "http://localhost:3000", "https://*.googleapis.com", "https://*.github.com", "https://REPLACE_ME.auth0.com",
      "https://accounts.google.com/o/oauth2/v2/auth", "https://github.com/login/oauth/authorize", "https://dev-5eqts7im.auth0.com/authorize", "https://dev-5eqts7im.auth0.com/login/oauth/token", "https://github.com/login/oauth/access_token",
      "https://asia-southeast1-joon-sandbox.cloudfunctions.net/explore-assistant-api",
      "https://explore-assistant-api-ken-hfcncejh6a-as.a.run.app",
      "https://explore-assistant-endpoint-136420034762.asia-southeast1.run.app",
      "http://localhost:8000"
    ]
    # external_api_urls: ["http://127.0.0.1:3000", "http://localhost:3000", "https://*.googleapis.com", "https://*.github.com", "https://REPLACE_ME.auth0.com"]
    oauth2_urls: ["https://accounts.google.com/o/oauth2/v2/auth", "https://github.com/login/oauth/authorize", "https://dev-5eqts7im.auth0.com/authorize", "https://dev-5eqts7im.auth0.com/login/oauth/token", "https://github.com/login/oauth/access_token"]
    scoped_user_attributes: ["user_value"]
    global_user_attributes: ["locale"]
  }
}
