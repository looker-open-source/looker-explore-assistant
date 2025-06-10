import React, { useEffect, useState, useRef } from 'react'
import { hot } from 'react-hot-loader/root'
import { Route, Switch, Redirect } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from './store'
import { useLookerFields } from './hooks/useLookerFields'
import { useBigQueryExamples } from './hooks/useBigQueryExamples'
import useSendCloudRunMessage from './hooks/useSendCloudRunMessage'
import { useAutoOAuth } from './hooks/useAutoOAuth'
import { useUserAttributes } from './hooks/useUserAttributes'
import { setInitialTestsCompleted } from './slices/assistantSlice'
import AgentPage from './pages/AgentPage'
import SettingsModal from './pages/AgentPage/Settings'
import ConnectionBanner from './components/Banner/ConnectionBanner'  // Import the new banner
import { Box, CircularProgress, Typography, Button } from '@material-ui/core'

// Debug flag for OAuth flow
const AUTH_DEBUG = true

const ExploreApp = () => {
  const dispatch = useDispatch()
  const { settings, bigQueryTestSuccessful, vertexTestSuccessful, oauth, userAttributesLoaded, initialTestsCompleted } = useSelector((state: RootState) => state.assistant) as any
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  
  // For tracking token validation attempts
  const tokenValidationCounter = useRef(0)
  const testsRunCounter = useRef(0)
  const lastCheckedToken = useRef('')
  
  // Load user attributes first
  const { isLoading: isLoadingUserAttributes, error: userAttributesError } = useUserAttributes()
  
  // Skip auto OAuth if settings modal is open
  const { isAuthenticating, hasValidToken, error: oauthError, validationInProgress } = useAutoOAuth(isSettingsOpen)

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

      AUTH_DEBUG && console.log('Running initial BQ and Cloud Run tests...')
      await testBigQuerySettings();
      await testCloudRunSettings();
      
      // Mark initial tests as completed
      dispatch(setInitialTestsCompleted(true))
      
      if (AUTH_DEBUG) {
        console.log('Initial tests completed. Results - BQ:', bigQueryTestSuccessful, 'Vertex:', vertexTestSuccessful)
      }
    };

    runInitialTests();    }, [userAttributesLoaded, initialTestsCompleted, testBigQuerySettings, testCloudRunSettings, settings, dispatch]);

  // CONDITIONAL SETTINGS MODAL: Only open if tests fail due to missing critical configuration
  useEffect(() => {
    if (!userAttributesLoaded || !initialTestsCompleted) {
      return // Wait for initialization to complete
    }

    // Only open settings modal if tests have failed and we're missing critical configuration
    const hasCriticalMissingSettings = !settings['google_oauth_client_id']?.value || 
                                      !settings['cloud_run_service_url']?.value

    const testsHaveFailed = !bigQueryTestSuccessful || !vertexTestSuccessful

    if (AUTH_DEBUG) {
      console.log('===== Settings Modal Decision =====')
      console.log('User attributes loaded:', userAttributesLoaded)
      console.log('Initial tests completed:', initialTestsCompleted)
      console.log('Tests have failed:', testsHaveFailed)
      console.log('Has critical missing settings:', hasCriticalMissingSettings)
      console.log('Current settings modal state:', isSettingsOpen)
    }

    if (testsHaveFailed && hasCriticalMissingSettings && !isSettingsOpen) {
      AUTH_DEBUG && console.log('Opening settings modal due to failed tests and missing critical configuration')
      setIsSettingsOpen(true)
    }
  }, [userAttributesLoaded, initialTestsCompleted, bigQueryTestSuccessful, vertexTestSuccessful, settings, isSettingsOpen]);

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

  // Show loading state while user attributes are being loaded
  if (isLoadingUserAttributes || !userAttributesLoaded) {
    AUTH_DEBUG && console.log('Showing user attributes loading indicator')
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

  // Always show banner initially since we're not using localStorage anymore
  const bannerInitialState = true

  return (
    <>
      <SettingsModal
        open={isSettingsOpen}
        onClose={() => {
          AUTH_DEBUG && console.log('Settings modal closed')
          setIsSettingsOpen(false)
        }}
      />
      {bigQueryTestSuccessful && vertexTestSuccessful ? (
        <>
          <ConnectionBanner initialVisible={bannerInitialState} />
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
            <Typography variant="body2" style={{ color: vertexTestSuccessful ? '#4caf50' : '#f44336' }}>
              Cloud Run Test: {vertexTestSuccessful ? '✅ Passed' : '❌ Failed'}
            </Typography>
          </Box>
        </Box>
      )}
    </>
  )
}

export const App = hot(ExploreApp)
