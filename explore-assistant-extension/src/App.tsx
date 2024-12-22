import React, { useEffect, useState } from 'react'
import { hot } from 'react-hot-loader/root'
import { Route, Switch, Redirect, useLocation} from 'react-router-dom'
import { useLookerFields } from './hooks/useLookerFields'
import { useBigQueryExamples } from './hooks/useBigQueryExamples'
import AgentPage from './pages/AgentPage'
import { useOAuthAuthentication } from './hooks/useOAuthAuthentication'; // Import custom hook

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
  const [isAuthenticated, setIsAuthenticated] = useState(false); // Track authentication status
  const authenticate = useOAuthAuthentication(); // OAuth authentication function

  // Load dimensions, measures, and examples into the state
  useLookerFields();
  useBigQueryExamples();

  const handleOAuthClick = async () => {
    try {
      const oauthResult = await authenticate(); // Trigger OAuth authentication when button is clicked

      if (oauthResult) {
        // Handle OAuth result (e.g., store the token, redirect, etc.)
        console.log('OAuth successful', oauthResult);
        setIsAuthenticated(true); // Mark as authenticated
      } else {
        console.error('OAuth failed');
      }
    } catch (error) {
      console.error('Error during OAuth:', error);
    }
  };

  return (
    <>
      <Switch>
        <Route path="/index" exact>
            <div>
              <button onClick={handleOAuthClick}>Authenticate with Google</button>
            </div>
          <AgentPage />
        </Route>
        <Route path="/oauth/callback" exact>
          <OAuthCallbackPage /> {/* Handle the OAuth callback here */}
        </Route>
        <Route>
          <Redirect to="/index" />
        </Route>
      </Switch>

      {/* Only show the OAuth button if not authenticated */}
    </>
  )
}

export const App = hot(ExploreApp)
