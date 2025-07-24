-- Sample Areas Table Setup for Looker Explore Assistant
-- This script creates a sample areas table that maps business areas to explore keys

-- Create the areas table
CREATE TABLE IF NOT EXISTS `your_project.your_dataset.areas` (
  area STRING,
  explore_key STRING,
  description STRING,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Insert sample data
-- Replace these with your actual explore keys and business areas
INSERT INTO `your_project.your_dataset.areas` (area, explore_key, description) VALUES
  ('Sales & Revenue', 'ecommerce:order_items', 'Order items and sales transactions'),
  ('Sales & Revenue', 'ecommerce:orders', 'Order header information'),
  ('Sales & Revenue', 'sales_analytics:deals', 'Sales deals and pipeline'),
  
  ('Customer Analytics', 'ecommerce:users', 'Customer demographics and behavior'),
  ('Customer Analytics', 'marketing:user_behavior', 'User interaction and engagement'),
  ('Customer Analytics', 'support:customer_tickets', 'Customer support interactions'),
  
  ('Marketing & Campaign', 'marketing:campaigns', 'Marketing campaign performance'),
  ('Marketing & Campaign', 'marketing:email_stats', 'Email marketing metrics'),
  ('Marketing & Campaign', 'marketing:social_media', 'Social media engagement'),
  
  ('Operations', 'inventory:stock_levels', 'Product inventory tracking'),
  ('Operations', 'shipping:logistics', 'Shipping and fulfillment'),
  ('Operations', 'support:agent_performance', 'Support team metrics'),
  
  ('Finance', 'finance:revenue_recognition', 'Revenue accounting'),
  ('Finance', 'finance:expenses', 'Company expenses'),
  ('Finance', 'finance:budgets', 'Budget planning and tracking');

-- Example LookML view for the areas table
/*
view: areas {
  sql_table_name: `your_project.your_dataset.areas` ;;
  
  dimension: area {
    type: string
    sql: ${TABLE}.area ;;
    description: "Business area or domain"
  }
  
  dimension: explore_key {
    type: string
    sql: ${TABLE}.explore_key ;;
    description: "Explore key in format model:explore_name"
  }
  
  dimension: description {
    type: string
    sql: ${TABLE}.description ;;
    description: "Description of what this explore contains"
  }
  
  dimension_group: created {
    type: time
    timeframes: [raw, date, week, month, quarter, year]
    sql: ${TABLE}.created_at ;;
  }
}

explore: areas {
  description: "Areas and their associated explore keys for the Explore Assistant"
}
*/
