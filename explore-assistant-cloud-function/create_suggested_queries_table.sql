-- SQL script to create the suggested_golden_queries table in BigQuery
-- Run this in your BigQuery console or using the bq command line tool

-- Create the suggested_golden_queries table
CREATE TABLE IF NOT EXISTS `ml-accelerator-dbarr.explore_assistant.suggested_golden_queries` (
  explore_key STRING NOT NULL,
  prompt STRING NOT NULL,
  explore_params STRING NOT NULL,  -- JSON string containing the explore parameters
  user_id STRING NOT NULL,         -- Email of the user who provided the feedback
  timestamp FLOAT64 NOT NULL,      -- Unix timestamp when the feedback was recorded
  created_at STRING NOT NULL,      -- Human-readable timestamp
  approved BOOLEAN NOT NULL,       -- Whether this suggestion has been approved
  feedback_type STRING NOT NULL,   -- Type of feedback (e.g., 'user_correction')
  
  -- Additional metadata columns for tracking
  id STRING DEFAULT (GENERATE_UUID()) NOT NULL,  -- Unique identifier
  created_date DATE DEFAULT (CURRENT_DATE())     -- Date partition for performance
)
CLUSTER BY explore_key, feedback_type;
)
PARTITION BY created_date
OPTIONS (
  description = "Table for storing user-suggested improvements to golden queries based on feedback",
  labels = [("environment", "production"), ("component", "explore-assistant")]
);

-- Create a view for easy querying of recent suggestions
CREATE OR REPLACE VIEW `ml-accelerator-dbarr.explore_assistant.recent_suggestions` AS
SELECT 
  explore_key,
  prompt,
  JSON_EXTRACT_SCALAR(explore_params, '$.fields') as fields,
  JSON_EXTRACT_SCALAR(explore_params, '$.vis_config.type') as visualization_type,
  user_id,
  DATETIME(TIMESTAMP_SECONDS(CAST(timestamp AS INT64))) as feedback_datetime,
  approved,
  feedback_type,
  id
FROM `ml-accelerator-dbarr.explore_assistant.suggested_golden_queries`
WHERE created_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
ORDER BY timestamp DESC;

-- Grant necessary permissions (adjust as needed for your organization)
-- GRANT `roles/bigquery.dataEditor` ON TABLE `ml-accelerator-dbarr.explore_assistant.suggested_golden_queries` TO "serviceAccount:your-cloud-run-service-account@your-project.iam.gserviceaccount.com";
