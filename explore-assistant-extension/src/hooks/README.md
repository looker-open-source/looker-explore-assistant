# Connection Failure Detection Hooks

This directory contains hooks for detecting and handling connection failures in the Looker Explore Assistant extension.

## useConnectionFailureDetection

A low-level hook that provides connection failure detection with retry logic.

### Features:
- Detects connection-related errors
- Implements retry logic with configurable attempts and delays
- Provides callbacks for failure events
- Tracks connection state and retry count

### Usage:
```typescript
const {
  isConnecting,
  connectionError,
  retryCount,
  hasReachedMaxRetries,
  handleError,
  handleConnectionSuccess,
  setConnecting,
  resetConnectionState,
} = useConnectionFailureDetection({
  maxRetries: 3,
  retryDelay: 2000,
  onConnectionFailure: (info) => console.warn('Connection failed', info),
  onMaxRetriesReached: (info) => console.error('Max retries reached', info),
  enableLogging: true,
})
```

## useCheckForConnectionFailure

A higher-level hook that combines connection failure detection with automatic handling of database connection issues.

### Features:
- All features from `useConnectionFailureDetection`
- Automatically opens `/accounts` page when database connection failures occur
- Distinguishes between database and non-database connection errors
- Provides utility function to manually open accounts page

### Usage:
```typescript
const {
  isConnecting,
  connectionError,
  retryCount,
  hasReachedMaxRetries,
  handleError,
  handleConnectionSuccess,
  setConnecting,
  resetConnectionState,
  isDatabaseConnectionError,
  openAccountsPage,
} = useCheckForConnectionFailure({
  maxRetries: 3,
  retryDelay: 2000,
  openAccountsPageOnFailure: true,
  customFailureHandler: (info) => {
    // Custom handling logic
  },
  enableLogging: true,
})
```

## Integration with ExploreEmbed

The `ExploreEmbed` component uses `useCheckForConnectionFailure` to:

1. **Monitor embed connections**: Detect when the Looker embed fails to connect
2. **Implement retry logic**: Automatically retry failed connections up to 3 times
3. **Handle database errors**: When database connection errors occur and max retries are reached, automatically open the accounts page using `extensionSDK.openBrowserWindow('/accounts', '_blank')`
4. **Provide user feedback**: Show connection status and error messages to users

### Connection Error Detection

The hooks identify connection errors by checking for these patterns in error messages:
- Network-related errors (network error, connection failed, timeout, etc.)
- Database-specific errors (database connection, SQL error, authentication failed, etc.)
- Looker-specific errors (looker connection, explore connection, embed sdk, etc.)
- Database platform errors (BigQuery, Snowflake, Redshift, etc.)

### Database Error Handling

When database connection errors are detected and max retries are reached:
1. The error is logged with context information
2. `extensionSDK.openBrowserWindow('/accounts', '_blank')` is called to open the accounts page
3. Users can review and update their database connection settings
4. Enhanced error messages provide guidance to users

## Testing

Both hooks include comprehensive unit tests covering:
- Basic functionality and state management
- Error detection and classification
- Retry logic and max retry handling
- ExtensionSDK integration
- Error boundary conditions

Run tests with:
```bash
npm test -- --testPathPattern=useConnectionFailureDetection
npm test -- --testPathPattern=useCheckForConnectionFailure
```
