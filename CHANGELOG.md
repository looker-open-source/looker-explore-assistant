# Changelog
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
