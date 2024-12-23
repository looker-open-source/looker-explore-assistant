import { useContext } from 'react';
import { ExtensionContext } from '@looker/extension-sdk-react';
import process from 'process';

export const useOAuthAuthentication = () => {
  const { extensionSDK } = useContext(ExtensionContext);

  if (!extensionSDK) {
    console.error('extensionSDK is undefined or not available');
    return async () => {};  // Return a no-op function if SDK is not available
  }

  const authenticate = async () => {
    try {
      // Generate a random state for CSRF protection
      const state = Math.random().toString(36).substring(7); // Simple random string as state
      // console.log('OAUTH FLOW : Generated state:', state);  // Log the generated state for debugging

      // OAuth parameters
      const client_id = process.env.OAUTH_CLIENT_ID || '';
      const authParameters = {
        client_id: client_id,
        scope: 'https://www.googleapis.com/auth/userinfo.profile',
        response_type: 'token',
        prompt: 'consent',
        state, // Include the generated state
        access_type: 'online'
      };

      console.log('OAUTH FLOW : Auth Parameters:', authParameters); // Log auth parameters

      // The authEndpoint is where the user is redirected for OAuth
      const authEndpoint = 'https://accounts.google.com/o/oauth2/v2/auth';
      // console.log('OAUTH FLOW : Auth Endpoint:', authEndpoint);  // Log the auth endpoint

      // Initiate OAuth authentication via Looker SDK
      const response = await extensionSDK.oauth2Authenticate(authEndpoint, authParameters);

      console.log('OAUTH FLOW : OAuth response:', response);  // Log the OAuth response for debugging

      // Assuming the response contains the access token and expiry time
      const { access_token, expires_in } = response;
      console.log('OAUTH FLOW : OAuth Authentication Successful.');

      // Return the token and expiry time
      return { access_token, expires_in };
    } catch (error) {
      console.error('OAuth Authentication Failed:', error);
      throw error;  // Rethrow error to allow handling at a higher level
    }
  };

  return authenticate;
};
