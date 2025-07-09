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
const TOKEN_DEBUG = false

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
  const IDENTITY_TOKEN = settings['identity_token']?.value as string || ''
  const GOOGLE_SCOPES = 'openid email profile'

  // Use Redux state instead of local state
  const {
    isAuthenticating,
    validationInProgress,
    skipAutoAuth,
    hasValidToken,
    error
  } = oauth

  // Helper function to check if ID token is fresh enough
  const isTokenFresh = async (token: string): Promise<boolean> => {
    try {
      // For ID tokens (JWTs), we can decode and check expiration locally
      const payload = JSON.parse(atob(token.split('.')[1]))
      const now = Math.floor(Date.now() / 1000)
      const expiresAt = payload.exp
      const hasRequiredFields = payload.email && payload.aud
      
      TOKEN_DEBUG && console.log('ID token expires at:', new Date(expiresAt * 1000).toISOString())
      TOKEN_DEBUG && console.log('Has required fields (email, aud):', hasRequiredFields)
      
      // Token is fresh if it has required fields and doesn't expire soon
      const isFresh = hasRequiredFields && expiresAt > (now + TOKEN_EXPIRY_THRESHOLD)
      TOKEN_DEBUG && console.log('ID token is fresh:', isFresh)
      
      return isFresh
    } catch (error) {
      TOKEN_DEBUG && console.log('Error checking ID token freshness:', error)
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
        console.log('Has Token:', !!IDENTITY_TOKEN)
        console.log('Token length (if exists):', IDENTITY_TOKEN ? IDENTITY_TOKEN.length : 0)
      }

      // Reset authenticating state on fresh mount if it's stuck
      // if (isAuthenticating && Date.now() - mountTime.current < 20000) {
      //   TOKEN_DEBUG && console.log('Clearing stuck authenticating state on fresh mount. If you see this message often, please comment out useAutoOauth line 86')
      //   dispatch(setOAuthAuthenticating(false))
      //   return
      // }

      // Skip if parameters indicate we should skip, or if we've already attempted successfully
      if (skipAutoAuthParam || skipAutoAuth || hasAttemptedOAuth.current) {
        TOKEN_DEBUG && console.log('Skipping OAuth flow due to flags or already attempted')
        return
      }
      
      // Skip if validation is in progress to avoid race conditions
      if (validationInProgress) {
        TOKEN_DEBUG && console.log('Token validation already in progress, skipping')
        return
      }
      
      // Skip if already authenticating to avoid duplicate OAuth flows
      if (isAuthenticating) {
        TOKEN_DEBUG && console.log('OAuth already in progress, skipping duplicate request')
        return
      }

      // Must have client ID to proceed
      if (!GOOGLE_CLIENT_ID) {
        TOKEN_DEBUG && console.log('No Google Client ID configured, skipping OAuth')
        return
      }

      try {
        // Clear any previous error
        dispatch(setOAuthError(null))
        
        // Always check token freshness on initial load, even if we have one
        let needsNewToken = !IDENTITY_TOKEN
        
        if (IDENTITY_TOKEN) {
          TOKEN_DEBUG && console.log('Checking existing token freshness...')
          dispatch(setOAuthValidationInProgress(true))
          
          const tokenIsFresh = await isTokenFresh(IDENTITY_TOKEN)
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
            response_type: 'id_token',
            nonce: Math.random().toString(36).substring(2, 15), // Required for ID token
            }
          )

          const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('OAuth timeout after 30 seconds')), 30000)
          })

          const response = await Promise.race([oauthPromise, timeoutPromise]) as any

          TOKEN_DEBUG && console.log('OAuth authentication completed, response received')
          const { id_token } = response
          if (id_token) {
            TOKEN_DEBUG && console.log('Received new ID token, length:', id_token.length)
            dispatch(setSetting({ id: 'identity_token', value: id_token }))
            console.log('ID token automatically obtained')
            
            // Set as successful validation
            dispatch(setOAuthLastValidation(Date.now()))
            dispatch(setOAuthHasValidToken(true))
            
            // Mark that we've successfully completed OAuth
            hasAttemptedOAuth.current = true
            
            if (TOKEN_DEBUG) {
              // Check if the token was actually saved
              setTimeout(() => {
                const storeAfterDispatch = store.getState?.() as any
                const assistantState = storeAfterDispatch?.assistant
                const savedToken = assistantState?.settings?.identity_token?.value
                console.log('Token saved to Redux store:', !!savedToken)
                console.log('Saved token matches received token:', savedToken === id_token)
              }, 500)
            }
          } else {
            TOKEN_DEBUG && console.log('No ID token received from OAuth flow')
            throw new Error('No ID token received from OAuth flow')
          }
        }
      } catch (error) {
        console.error('Automatic OAuth authentication failed:', error)
        TOKEN_DEBUG && console.log('OAuth error details:', error)
        
        // Set error state
        dispatch(setOAuthError(error instanceof Error ? error.message : 'OAuth authentication failed'))
        dispatch(setOAuthHasValidToken(false))
        
        // Don't reset the attempt flag so we can try again if needed
        TOKEN_DEBUG && console.log('OAuth failed, not resetting attempt flag to allow manual retry')
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
  }, [GOOGLE_CLIENT_ID, IDENTITY_TOKEN, extensionSDK, dispatch, skipAutoAuthParam, skipAutoAuth, isAuthenticating, validationInProgress])

  return { 
    isAuthenticating,
    hasValidToken,
    error,
    validationInProgress
  }
}