import React, { useEffect, useState, useRef } from 'react'
import { hot } from 'react-hot-loader/root'
import { Route, Switch, Redirect } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from './store'
import { useLookerFields } from './hooks/useLookerFields'
import { useBigQueryExamples } from './hooks/useBigQueryExamples'
import useSendCloudRunMessage from './hooks/useSendCloudRunMessage'
import { useAutoOAuth } from './hooks/useAutoOAuth'
import { useExtensionContext } from './hooks/useExtensionContext'
import { useConnectionCheck } from './hooks/useOAuthConnectionCheck'
import {
  resetExploreAssistant,
  setBigQueryTestSuccessful,
  setVertexTestSuccessful,  // Add this import
  setInitialTestsCompleted,
} from './slices/assistantSlice'
import AgentPage from './pages/AgentPage'
import SettingsModal from './pages/AgentPage/Settings'
import { Box, CircularProgress, Typography, Button } from '@material-ui/core'

// Debug flag for OAuth flow
const AUTH_DEBUG = false

const ExploreApp = () => {
  const dispatch = useDispatch()
  const { settings, bigQueryTestSuccessful, vertexTestSuccessful, oauth, userAttributesLoaded, initialTestsCompleted } = useSelector((state: RootState) => state.assistant) as any
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  
  // For tracking token validation attempts
  const tokenValidationCounter = useRef(0)
  const testsRunCounter = useRef(0)
  const lastCheckedToken = useRef('')
  
  // Load extension context first (renamed for clarity but keeping same interface)
  const { isLoading: isLoadingExtensionContext, error: extensionContextError } = useExtensionContext()
  
  // Skip auto OAuth if settings modal is open
  const { isAuthenticating, hasValidToken, error: oauthError, validationInProgress } = useAutoOAuth(isSettingsOpen)

  // Check all connections once per app session
  useConnectionCheck()

  useLookerFields()
  const { testBigQuerySettings } = useBigQueryExamples()
  const { testCloudRunSettings } = useSendCloudRunMessage()

  // Add timeout for OAuth process
  const [showFallbackUI, setShowFallbackUI] = useState(false)
  
  useEffect(() => {
    const oauthTimeout = setTimeout(() => {
      if (isAuthenticating) {
        console.warn('OAuth taking too long, showing fallback UI')
        setShowFallbackUI(true)
      }
    }, 15000) // 15 second timeout

    return () => clearTimeout(oauthTimeout)
  }, [isAuthenticating])

  // NEW INITIALIZATION FLOW: User attributes → Tests → Conditional settings modal
  useEffect(() => {
    const runInitialTests = async () => {
      if (!userAttributesLoaded || initialTestsCompleted) {
        if (AUTH_DEBUG) {
          console.log('Skipping tests: userAttributesLoaded=', userAttributesLoaded, 'initialTestsCompleted=', initialTestsCompleted)
        }
        return
      }

      testsRunCounter.current++
      
      if (AUTH_DEBUG) {
        console.log('===== Initial App Test Execution =====')
        console.log('Tests run count:', testsRunCounter.current)
        console.log('User attributes loaded:', userAttributesLoaded)
        console.log('BigQuery test status:', bigQueryTestSuccessful)
        console.log('Vertex test status:', vertexTestSuccessful)
        console.log('Cloud Run URL configured:', !!settings['cloud_run_service_url']?.value)
      }
      
      // Validate existing token before running tests
      const existingToken = settings['oauth2_token']?.value;
      
      if (existingToken) {
        lastCheckedToken.current = existingToken
        tokenValidationCounter.current++
        
        if (AUTH_DEBUG) {
          console.log('Token validation attempt #', tokenValidationCounter.current)
        }
        
        try {
          const tokenInfo = await fetch('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=' + existingToken);
          if (AUTH_DEBUG) {
            console.log('Token validation status:', tokenInfo.status)
          }
          
          if (!tokenInfo.ok) {
            console.error('Existing OAuth token is invalid during initial tests');
            // Don't open settings modal here - let the tests fail and then decide
          } else if (AUTH_DEBUG) {
            const tokenData = await tokenInfo.clone().json();
            console.log('Valid token expires in:', tokenData.expires_in, 'seconds')
          }
        } catch (error) {
          AUTH_DEBUG && console.log('Error validating token in App component:', error)
          // Don't open settings modal here - let the tests fail and then decide
        }
      } else if (AUTH_DEBUG) {
        console.log('No token available for initial tests')
      }

      AUTH_DEBUG && console.log('Running initial tests...')
      
      // Run BigQuery test
      console.log('Starting BigQuery test...')
      const bqResult = await testBigQuerySettings();
      console.log('BigQuery test result:', bqResult)
      
      // Run Cloud Run test only if URL is configured
      let cloudRunResult = true; // Default to true if no URL configured
      const cloudRunUrl = settings['cloud_run_service_url']?.value
      const hasOAuthToken = !!settings['oauth2_token']?.value
      
      console.log('Cloud Run URL check:', cloudRunUrl || 'NOT SET')
      console.log('OAuth token check:', hasOAuthToken ? 'AVAILABLE' : 'NOT AVAILABLE')
      
      if (cloudRunUrl) {
        console.log('Starting Cloud Run test...')
        console.log('Will test URL:', cloudRunUrl)
        console.log('Using OAuth token:', hasOAuthToken)
        
        cloudRunResult = await testCloudRunSettings();
        console.log('Cloud Run test result:', cloudRunResult)
        
        // Update Redux state with Cloud Run test result
        dispatch(setVertexTestSuccessful(cloudRunResult))
        console.log('Dispatched setVertexTestSuccessful:', cloudRunResult)
      } else {
        console.log('Cloud Run URL not configured, skipping Cloud Run test')
        // If no URL configured, consider it as "passed" since it's optional
        dispatch(setVertexTestSuccessful(true))
        console.log('Dispatched setVertexTestSuccessful: true (no URL configured)')
      }
      
      // ONLY mark initial tests as completed AFTER both tests are done
      dispatch(setInitialTestsCompleted(true))
      
      if (AUTH_DEBUG) {
        console.log('Initial tests completed. Results - BQ:', bqResult, 'Cloud Run:', cloudRunResult)
        console.log('Redux state - BQ:', bigQueryTestSuccessful, 'Vertex:', vertexTestSuccessful)
      }
    };

    runInitialTests();
  }, [userAttributesLoaded, initialTestsCompleted, testBigQuerySettings, testCloudRunSettings, settings['cloud_run_service_url']?.value, settings['oauth2_token']?.value, dispatch]);

  // CONDITIONAL SETTINGS MODAL: Only open if tests fail due to missing critical configuration
  useEffect(() => {
    if (!userAttributesLoaded || !initialTestsCompleted) {
      return // Wait for initialization to complete
    }

    // Only open settings modal if tests have failed and we're missing critical configuration
    const hasCriticalMissingSettings = !settings['google_oauth_client_id']?.value || 
                                      !settings['cloud_run_service_url']?.value

    // Check if tests have failed - include Cloud Run test only if URL is configured
    const cloudRunUrlConfigured = !!settings['cloud_run_service_url']?.value
    const testsHaveFailed = !bigQueryTestSuccessful || (cloudRunUrlConfigured && !vertexTestSuccessful)

    if (AUTH_DEBUG) {
      console.log('===== Settings Modal Decision =====')
      console.log('User attributes loaded:', userAttributesLoaded)
      console.log('Initial tests completed:', initialTestsCompleted)
      console.log('Cloud Run URL configured:', cloudRunUrlConfigured)
      console.log('Tests have failed:', testsHaveFailed)
      console.log('Has critical missing settings:', hasCriticalMissingSettings)
      console.log('Current settings modal state:', isSettingsOpen)
    }

    if (testsHaveFailed && hasCriticalMissingSettings && !isSettingsOpen) {
      AUTH_DEBUG && console.log('Opening settings modal due to failed tests and missing critical configuration')
      setIsSettingsOpen(true)
    }
  }, [userAttributesLoaded, initialTestsCompleted, bigQueryTestSuccessful, vertexTestSuccessful, settings['google_oauth_client_id']?.value, settings['cloud_run_service_url']?.value, isSettingsOpen]);

  // Show error state if OAuth fails or times out
  if (oauthError || showFallbackUI) {
    return (
      <>
        <SettingsModal
          open={isSettingsOpen}
          onClose={() => {
            AUTH_DEBUG && console.log('Settings modal closed')
            setIsSettingsOpen(false)
            setShowFallbackUI(false)
          }}
        />
        <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" height="100vh" p={3}>
          <Typography variant="h6" color="error" gutterBottom>
            {oauthError || 'Authentication Error'}
          </Typography>
          <Typography variant="body1" gutterBottom align="center">
            There seems to be an issue with authentication. Please check your settings and try again.
          </Typography>
          <Box mt={2}>
            <Button 
              variant="contained" 
              color="primary"
              onClick={() => {
                setIsSettingsOpen(true)
                setShowFallbackUI(false)
              }}
            >
              Open Settings
            </Button>
          </Box>
        </Box>
      </>
    )
  }

  // Show loading state while extension context is being loaded
  if (isLoadingExtensionContext || !userAttributesLoaded) {
    AUTH_DEBUG && console.log('Showing extension context loading indicator')
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
        <CircularProgress />
        <Box ml={2}>Loading configuration...</Box>
      </Box>
    )
  }

  if (isAuthenticating) {
    AUTH_DEBUG && console.log('Showing authentication progress indicator')
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
        <CircularProgress />
        <Box ml={2}>Authenticating with Google...</Box>
      </Box>
    )
  }
  AUTH_DEBUG && console.log('Rendering main app view. Settings open:', isSettingsOpen, 'BQ/Vertex tests successful:', bigQueryTestSuccessful, vertexTestSuccessful)

  return (
    <>
      <SettingsModal
        open={isSettingsOpen}
        onClose={() => {
          AUTH_DEBUG && console.log('Settings modal closed')
          setIsSettingsOpen(false)
        }}
      />
      {bigQueryTestSuccessful && (settings['cloud_run_service_url']?.value ? vertexTestSuccessful : true) ? (
        <>
          <Switch>
            <Route path="/index" exact>
              <AgentPage />
            </Route>
            <Route>
              <Redirect to="/index" />
            </Route>
          </Switch>
        </>
      ) : (
        // Show setup UI when tests haven't passed
        <Box display="flex" flexDirection="column" justifyContent="center" alignItems="center" height="100vh" p={3}>
          <Typography variant="h5" gutterBottom>
            Welcome to Explore Assistant
          </Typography>
          <Typography variant="body1" gutterBottom align="center">
            Please complete the initial setup to get started.
          </Typography>
          <Box mt={2}>
            <Button 
              variant="contained" 
              color="primary"
              onClick={() => setIsSettingsOpen(true)}
            >
              Open Settings
            </Button>
          </Box>
          <Box mt={3}>
            <Typography variant="body2" style={{ color: bigQueryTestSuccessful ? '#4caf50' : '#f44336' }}>
              BigQuery Test: {bigQueryTestSuccessful ? '✅ Passed' : '❌ Failed'}
            </Typography>
            {settings['cloud_run_service_url']?.value && (
              <Typography variant="body2" style={{ color: vertexTestSuccessful ? '#4caf50' : '#f44336' }}>
                Cloud Run Test: {vertexTestSuccessful ? '✅ Passed' : '❌ Failed'}
              </Typography>
            )}
            {!settings['cloud_run_service_url']?.value && (
              <Typography variant="body2" style={{ color: '#ff9800' }}>
                Cloud Run Test: ⚠️ Not configured
              </Typography>
            )}
          </Box>
        </Box>
      )}
    </>
  )
}

export const App = hot(ExploreApp)
