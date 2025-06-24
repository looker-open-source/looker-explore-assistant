import { useEffect, useRef } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { useContext } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState, store } from '../store'
import { 
  AssistantState, 
  setSetting,
  setOAuthAuthenticating,
  setOAuthValidationInProgress,
  setOAuthLastValidation,
  setOAuthError,
  setOAuthHasValidToken
} from '../slices/assistantSlice'

// Debug configuration
const TOKEN_DEBUG = true

// Token expiration threshold (if token expires in less than this time, refresh it)
const TOKEN_EXPIRY_THRESHOLD = 10 * 60 // 10 minutes in seconds

export const useAutoOAuth = (skipAutoAuthParam = false) => {
  const { extensionSDK } = useContext(ExtensionContext)
  const dispatch = useDispatch()
  
  // Track if we've run OAuth on this mount to prevent multiple attempts
  const hasAttemptedOAuth = useRef(false)
  const mountTime = useRef<number>(Date.now())
  
  const { settings, oauth } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )

  const GOOGLE_CLIENT_ID = settings['google_oauth_client_id']?.value as string || ''
  const OAUTH2_TOKEN = settings['oauth2_token']?.value as string || ''
  const GOOGLE_SCOPES = 'https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/userinfo.email'

  // Use Redux state instead of local state
  const {
    isAuthenticating,
    validationInProgress,
    skipAutoAuth,
    hasValidToken,
    error
  } = oauth

  // Helper function to check if token is fresh enough
  const isTokenFresh = async (token: string): Promise<boolean> => {
    try {
      const response = await fetch(`https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=${token}`)
      if (!response.ok) {
        TOKEN_DEBUG && console.log('Token validation failed with status:', response.status)
        return false
      }
      
      const tokenDetails = await response.json()
      const expiresIn = parseInt(tokenDetails.expires_in || '0')
      const hasRequiredScopes = tokenDetails.scope && 
        tokenDetails.scope.includes('https://www.googleapis.com/auth/cloud-platform') &&
        tokenDetails.scope.includes('https://www.googleapis.com/auth/userinfo.email')
      
      TOKEN_DEBUG && console.log('Token expires in:', expiresIn, 'seconds')
      TOKEN_DEBUG && console.log('Has required scopes:', hasRequiredScopes)
      
      // Token is fresh if it has required scopes and doesn't expire soon
      const isFresh = hasRequiredScopes && expiresIn > TOKEN_EXPIRY_THRESHOLD
      TOKEN_DEBUG && console.log('Token is fresh:', isFresh)
      
      return isFresh
    } catch (error) {
      TOKEN_DEBUG && console.log('Error checking token freshness:', error)
      return false
    }
  }

  useEffect(() => {
    const doAutoOAuth = async () => {
      if (TOKEN_DEBUG) {
        console.log('===== OAuth Debug Info =====')
        console.log('Skip Auth Flag (param):', skipAutoAuthParam)
        console.log('Skip Auth Flag (Redux):', skipAutoAuth)
        console.log('isAuthenticating State:', isAuthenticating)
        console.log('Has attempted OAuth on this mount:', hasAttemptedOAuth.current)
        console.log('Component mount time:', new Date(mountTime.current).toISOString())
        console.log('Time since mount (ms):', Date.now() - mountTime.current)
        console.log('Has Client ID:', !!GOOGLE_CLIENT_ID)
        console.log('Has Token:', !!OAUTH2_TOKEN)
        console.log('Token length (if exists):', OAUTH2_TOKEN ? OAUTH2_TOKEN.length : 0)
      }

      // Skip if parameters indicate we should skip, or if already authenticating, or if we've already attempted
      if (skipAutoAuthParam || skipAutoAuth || isAuthenticating || hasAttemptedOAuth.current) {
        TOKEN_DEBUG && console.log('Skipping OAuth flow due to flags or already attempted')
        return
      }
      
      // Skip if validation is in progress to avoid race conditions
      if (validationInProgress) {
        TOKEN_DEBUG && console.log('Token validation already in progress, skipping')
        return
      }

      // Must have client ID to proceed
      if (!GOOGLE_CLIENT_ID) {
        TOKEN_DEBUG && console.log('No Google Client ID configured, skipping OAuth')
        return
      }

      // Mark that we've attempted OAuth on this mount
      hasAttemptedOAuth.current = true

      try {
        // Clear any previous error
        dispatch(setOAuthError(null))
        
        // Always check token freshness on initial load, even if we have one
        let needsNewToken = !OAUTH2_TOKEN
        
        if (OAUTH2_TOKEN) {
          TOKEN_DEBUG && console.log('Checking existing token freshness...')
          dispatch(setOAuthValidationInProgress(true))
          
          const tokenIsFresh = await isTokenFresh(OAUTH2_TOKEN)
          needsNewToken = !tokenIsFresh
          
          if (tokenIsFresh) {
            TOKEN_DEBUG && console.log('Existing token is fresh and valid')
            dispatch(setOAuthLastValidation(Date.now()))
            dispatch(setOAuthHasValidToken(true))
            dispatch(setOAuthValidationInProgress(false))
            return
          } else {
            TOKEN_DEBUG && console.log('Existing token is stale or invalid, will refresh')
            dispatch(setOAuthHasValidToken(false))
          }
          
          dispatch(setOAuthValidationInProgress(false))
        } else {
          TOKEN_DEBUG && console.log('No existing token, will obtain new one')
        }

        if (needsNewToken) {
          console.log('Starting automatic OAuth flow')
          dispatch(setOAuthAuthenticating(true))

          TOKEN_DEBUG && console.log('Calling extensionSDK.oauth2Authenticate')
          
          // Add timeout for OAuth process
          const oauthPromise = extensionSDK.oauth2Authenticate(
            'https://accounts.google.com/o/oauth2/v2/auth',
            {
              client_id: GOOGLE_CLIENT_ID,
              scope: GOOGLE_SCOPES,
              response_type: 'token',
            }
          )

          const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('OAuth timeout after 30 seconds')), 30000)
          })

          const response = await Promise.race([oauthPromise, timeoutPromise]) as any

          TOKEN_DEBUG && console.log('OAuth authentication completed, response received')
          const { access_token } = response
          if (access_token) {
            TOKEN_DEBUG && console.log('Received new access token, length:', access_token.length)
            dispatch(setSetting({ id: 'oauth2_token', value: access_token }))
            console.log('OAuth token automatically obtained')
            
            // Set as successful validation
            dispatch(setOAuthLastValidation(Date.now()))
            dispatch(setOAuthHasValidToken(true))
            
            if (TOKEN_DEBUG) {
              // Check if the token was actually saved
              setTimeout(() => {
                const storeAfterDispatch = store.getState?.() as any
                const assistantState = storeAfterDispatch?.assistant
                const savedToken = assistantState?.settings?.oauth2_token?.value
                console.log('Token saved to Redux store:', !!savedToken)
                console.log('Saved token matches received token:', savedToken === access_token)
              }, 500)
            }
          } else {
            TOKEN_DEBUG && console.log('No access token received from OAuth flow')
            throw new Error('No access token received from OAuth flow')
          }
        }
      } catch (error) {
        console.error('Automatic OAuth authentication failed:', error)
        TOKEN_DEBUG && console.log('OAuth error details:', error)
        
        // Set error state
        dispatch(setOAuthError(error instanceof Error ? error.message : 'OAuth authentication failed'))
        dispatch(setOAuthHasValidToken(false))
        
        // Reset the attempt flag so we can try again on next mount/change
        hasAttemptedOAuth.current = false
      } finally {
        dispatch(setOAuthAuthenticating(false))
      }
    }

    doAutoOAuth()

    // Cleanup function that runs when the component unmounts
    return () => {
      if (TOKEN_DEBUG) {
        console.log('===== useAutoOAuth unmounting =====')
        console.log('Component was mounted for:', (Date.now() - mountTime.current) / 1000, 'seconds')
      }
    }
  }, [GOOGLE_CLIENT_ID, extensionSDK, dispatch, skipAutoAuthParam, skipAutoAuth, isAuthenticating, validationInProgress])

  return { 
    isAuthenticating,
    hasValidToken,
    error,
    validationInProgress
  }
}