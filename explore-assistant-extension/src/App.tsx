import React, { useEffect, useState } from 'react'
import { hot } from 'react-hot-loader/root'
import { Route, Switch, Redirect, useLocation} from 'react-router-dom'
import { useLookerFields } from './hooks/useLookerFields'
import { useBigQueryExamples } from './hooks/useBigQueryExamples'
import AgentPage from './pages/AgentPage'
import { useOAuthAuthentication } from './hooks/useOAuthAuthentication'; // Import custom hook
import { useDispatch, useSelector } from 'react-redux';
import AuthLoadingScreen from './components/Auth/AuthLoadingScreen'
import { setAuthenticated, setToken, setExpiry } from './slices/authSlice'
import { isTokenExpired } from './components/Auth/AuthProvider'


// OAuth Callback handler component
const OAuthCallbackPage = () => {
  const location = useLocation(); // To access the URL query params
  const [tokenData, setTokenData] = useState(null);

  useEffect(() => {
    // Capture the access token from the query parameters
    const params = new URLSearchParams(location.search);
    const accessToken = params.get('access_token');
    const error = params.get('error');

    if (error) {
      console.error('OAuth error:', error);
      // Handle OAuth failure (e.g., show an error message)
    }

    if (accessToken) {
      // Handle the successful OAuth response
      setTokenData({ accessToken });
      console.log('OAuth token:', accessToken);
      // You can now use the token (store it, send it to the backend, etc.)
    }
  }, [location.search]);

  return (
    <div>
      {tokenData ? (
        <div>
          <h1>OAuth Successful</h1>
          <p>Access Token: {tokenData.accessToken}</p>
        </div>
      ) : (
        <h1>Loading...</h1>
      )}
    </div>
  );
};

const ExploreApp = () => {
  const authenticate = useOAuthAuthentication()
  const dispatch = useDispatch()
  const { isAuthenticated, access_token, expires_in } = useSelector((state: RootState) => state.auth)


  // Load dimensions, measures, and examples into the state
  useLookerFields();
  useBigQueryExamples();

  const handleAuth = async () => {
    try {
      const authResult = await authenticate()
      if (authResult?.access_token) {
        const newExpiry = Date.now() + (authResult.expires_in * 1000)
        dispatch(setAuthenticated(true))
        dispatch(setToken(authResult.access_token))
        dispatch(setExpiry(newExpiry))
        localStorage.setItem('lastAuthTime', Date.now().toString())
      }
    } catch (error) {
      console.error('Auth failed:', error)
    }
  }

  if (!isAuthenticated || !access_token || isTokenExpired(access_token, expires_in)) {
    return <AuthLoadingScreen onAuthClick={handleAuth} />
  }

  return (
    <Switch>
      <Route path="/index" exact>
        <AgentPage />
      </Route>
      <Route path="/oauth/callback" exact>
        <OAuthCallbackPage />
      </Route>
      <Route>
        <Redirect to="/index" />
      </Route>
    </Switch>
  )
}

export const App = hot(ExploreApp)
