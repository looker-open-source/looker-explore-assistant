# Changelog


## V4.1 (Marketplace PR)
- Instead of using sql runner queries, the required data is modeled in LookML. This prevents the need for escalated privileges for users (ie use_sql_runner permission). 
  - Requires the use of a Looker block or remote project import.
- Environment variables previously built into the Frontend application are now entered in an admin menu of the UI and stored as user attributes. 
  - The compiled .js is now portable.
- Instead of calling a cloud function endpoint through the browser, this call is proxied through Looker. 
  - Allows a closed network design.
- Backend install flow available in Cloud Console (GCP Cloud Shell). 
  - Local IDE setup is now unnecessary.
- Cloud console flow for backend setup includes step by step instructions as well as Terraform script. 
  - This makes installation in an existing Google Project possible.


## V4.0 (Making it smarter)
- Updated Readme to provide clearer instructions and troubleshooting tips
- Simplified setup with a single shared environment file
- Improved bash scripts for example generation
- Added the ability to generate training prompts from trusted dashboards
- Improved error messages (added CORS headers) to improve the setup process
- Improved the accuracy of Explore Assistant returning the correct results by adding relevant context. Specific improvements include:
  - Date filters: Accuracy for basic, range, and complex date filters increased significantly (details in table below).
  - Field selection: Accuracy for selecting fields with pivots and dates has also improved.

## v3.1

### Added
- Explore dropdown for asking questions against different explores
  - only loads explores that exist in examples table on bigquery end
  - extension frontend picks up explores without redeployment of app
- Dynamic explore samples loaded from samples table in BigQuery
  - terraform update to deploy samples table
  - bigquery loader script update to upload samples per explore
  
## v3.0

### Added
- Multi-turn chat experience with:
  - summarization requests
  - multiple turns for updating an existing explore
  - refine the question asked to gemini
  - conversation with markdown support
- Example loader for generation and refinement examples
- Extension app loads examples on the main page to speed up querying

## v2.1

### Added
- Shared secret for the cloud function and explore assistant extension
- Terraform code for managing the token in the GCP Secrets Manager

## v2.0

There are many breaking changes in this version.

### Added
- Script to load examples into the database in `Extension Examples`.
- TypeScript definition in `Globals.d.ts`, removing the need for `styles.d.ts` in `Extension Framework Javascript App`.
- Use of SaSS for styles in `Extension Framework Javascript App`.
- React-router for routing between pages in `Extension Framework Javascript App`.
- Use of primitives from the Looker Component Library in `Extension Framework Javascript App`.
- Dotenv for loading environment variables into webpack in `Extension Framework Javascript App`.

### Changed
- Consolidated all terraform into one folder in `Extension Framework Backend`.
- Use of environment variables to trigger different behaviors, avoiding the need to overwrite variable files in `Extension Framework Backend`.
- Modules separation for each backend in `Extension Framework Backend`.
- Cloud function to present the same interface as `ML.GENERATE_TEXT`, taking in a prompt and parameters in `Extension Cloud Function`.
- Script adaptation for both local development and Google Cloud Function deployment in `Extension Cloud Function`.
- Loading of examples, dimensions, measures from the extension instead of the cloud function in `Extension Framework Javascript App`.
- Break-up of different React components into their own files in `Extension Framework Javascript App`.
- Assistant state storage using Redux Toolkit in `Extension Framework Javascript App`.
- Backend selection based on environment variables, with consistency between the cloud function and the BigQuery model in `Extension Framework Javascript App`.

### Removed
- `examples.json` and `thelook` files in `Extension Cloud Function`.
- Console logs to clean up code in `Extension Framework Javascript App`.
- Custom CSS as much as possible, replaced by Looker Component Library styling in `Extension Framework Javascript App`.
- Errors in TypeScript in `Extension Framework Javascript App`.

### Fixed
- TypeScript errors in `Extension Framework Javascript App`.

### Improved
- `.gitignore` for terraform in `Extension Framework Backend`.
