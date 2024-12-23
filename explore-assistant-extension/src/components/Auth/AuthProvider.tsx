import React, { useEffect } from 'react';
import { useOAuthAuthentication } from '../../hooks/useOAuthAuthentication';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../../store';
import { setAuthenticated, setToken, setExpiry } from '../../slices/authSlice';



interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const dispatch = useDispatch();
  const authenticate = useOAuthAuthentication();
  const { access_token, expires_in } = useSelector((state: RootState) => state.auth);
  
  const isTokenExpired = () => {
    console.group('Token Verification Check');
    console.log('Current token:', access_token);
    console.log('Expiry time:', new Date(expires_in).toLocaleString());
    console.log('Current time:',  new Date().toLocaleString());
    
    if (!expires_in) {
      console.log('No expiry time found, treating as expired');
      console.groupEnd();
      return true;
    }
    
    const expiryTime = new Date(expires_in).getTime();
    const currentTime = new Date().getTime();
    const isExpired = currentTime >= expiryTime;
    
    console.log('Token expired?', isExpired);
    console.log('Time until expiration:', (expiryTime - currentTime) / 1000, 'seconds');
    console.log('Expiry in local time:', new Date(expiryTime).toLocaleString());
    console.groupEnd();
    return isExpired;
  };

  useEffect(() => {
    console.group('Auth Provider Initialization');
    console.log('Page Load/Refresh detected');
    console.log('Redux Auth State:', { access_token, expires_in });

    const initializeAuth = async () => {
      if (!access_token || isTokenExpired()) {
        console.log('Starting new OAuth flow');
        try {
          const authResult = await authenticate();
          console.log('New Auth Result:', authResult);
          if (authResult?.access_token) {
            const newExpiry = Date.now() + (authResult.expires_in * 1000);
            dispatch(setAuthenticated(true));
            dispatch(setToken(authResult.access_token));
            dispatch(setExpiry(newExpiry));
            console.log('New token set with expiry:', new Date(newExpiry).toISOString());
          }
        } catch (error) {
          console.error('Auth flow failed:', error);
        }
      } else {
        console.log('Valid token found, continuing with existing session');
      }
    };

    initializeAuth();
    console.groupEnd();
  }, []);

  return <>{children}</>;
};

