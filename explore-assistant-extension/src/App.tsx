import React, { useEffect, useState, useRef } from 'react'
import { hot } from 'react-hot-loader/root'
import { Route, Switch, Redirect } from 'react-router-dom'
import { useSelector, useDispatch } from 'react-redux'
import { RootState } from './store'
import { useLookerFields } from './hooks/useLookerFields'
import { useBigQueryExamples } from './hooks/useBigQueryExamples'
import useSendVertexMessage from './hooks/useSendVertexMessage'
import { useAutoOAuth } from './hooks/useAutoOAuth'
import AgentPage from './pages/AgentPage'
import SettingsModal from './pages/AgentPage/Settings'
import ConnectionBanner from './components/Banner/ConnectionBanner'  // Import the new banner
import { Box, CircularProgress, Typography } from '@material-ui/core'

// Debug flag for OAuth flow
const AUTH_DEBUG = true

const ExploreApp = () => {
  const dispatch = useDispatch()
  const { settings, bigQueryTestSuccessful, vertexTestSuccessful } = useSelector((state: RootState) => state.assistant) as any
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  
  // For tracking token validation attempts
  const tokenValidationCounter = useRef(0)
  const testsRunCounter = useRef(0)
  const lastCheckedToken = useRef('')
  
  // Skip auto OAuth if settings modal is open
  const { isAuthenticating } = useAutoOAuth(isSettingsOpen)

  useLookerFields()
  const { testBigQuerySettings } = useBigQueryExamples()
  const { testVertexSettings } = useSendVertexMessage()

  useEffect(() => {
    const missingSettings = Object.values(settings).some((setting: any) => !setting?.value)
    if (AUTH_DEBUG) {
      console.log('===== App Component Settings Debug =====')
      console.log('Settings check - any missing?', missingSettings)
      console.log('OAuth client ID setting:', settings['google_oauth_client_id']?.value ? 'Present' : 'Missing')
      console.log('OAuth token setting:', settings['oauth2_token']?.value ? 'Present' : 'Missing')
      if (settings['oauth2_token']?.value) {
        const tokenFirstChars = settings['oauth2_token'].value.substr(0, 10)
        console.log('Token first chars:', tokenFirstChars + '...')
      }
    }

    if (missingSettings) {
      AUTH_DEBUG && console.log('Missing settings detected, opening settings modal')
      setIsSettingsOpen(true)
    }
  }, [settings])

  useEffect(() => {
    const runTests = async () => {
      testsRunCounter.current++
      
      // Validate existing token before running tests
      const existingToken = settings['oauth2_token']?.value;
      
      if (AUTH_DEBUG) {
        console.log('===== App Test Execution Debug =====')
        console.log('Tests run count:', testsRunCounter.current)
        console.log('bigQueryTestSuccessful:', bigQueryTestSuccessful)
        console.log('vertexTestSuccessful:', vertexTestSuccessful)
        console.log('Has OAuth token for tests:', !!existingToken)
        console.log('Token is same as last checked:', existingToken === lastCheckedToken.current)
      }
      
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
            console.error('Existing OAuth token is invalid, triggering re-authentication');
            setIsSettingsOpen(true);
            return;
          } else if (AUTH_DEBUG) {
            const tokenData = await tokenInfo.clone().json();
            console.log('Valid token expires in:', tokenData.expires_in, 'seconds')
          }
        } catch (error) {
          AUTH_DEBUG && console.log('Error validating token in App component:', error)
          setIsSettingsOpen(true);
          return;
        }
      } else if (AUTH_DEBUG) {
        console.log('No token available for tests')
      }

      AUTH_DEBUG && console.log('Running BQ and Vertex tests...')
      testBigQuerySettings();
      testVertexSettings();
    };

    if (!bigQueryTestSuccessful || !vertexTestSuccessful) {
      runTests();
    } else if (AUTH_DEBUG) {
      console.log('Tests already successful, skipping re-run')
    }
  }, [testBigQuerySettings, testVertexSettings, bigQueryTestSuccessful, vertexTestSuccessful, settings]);

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
      { bigQueryTestSuccessful && vertexTestSuccessful && (
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
      )}
    </>
  )
}

export const App = hot(ExploreApp)
