import { useEffect, useState, useRef } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { useContext } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState, store } from '../store'
import { AssistantState, setSetting } from '../slices/assistantSlice'

// Debug configuration
const TOKEN_DEBUG = true
const AUTH_WINDOW_DEBUG = true // Specifically for debugging the auth window appearing

export const useAutoOAuth = (skipAutoAuth = false) => {
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const { extensionSDK } = useContext(ExtensionContext)
  const dispatch = useDispatch()
  
  // Track last successful token validation to prevent unnecessary checks
  const lastSuccessfulValidation = useRef<number>(0)
  const validationInProgress = useRef<boolean>(false)
  const mountTime = useRef<number>(Date.now())
  
  const { settings } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )

  const GOOGLE_CLIENT_ID = settings['google_oauth_client_id']?.value as string || ''
  const OAUTH2_TOKEN = settings['oauth2_token']?.value as string || ''
  const GOOGLE_SCOPES = 'https://www.googleapis.com/auth/cloud-platform'

  // Track if oauth flow is in progress globally to prevent duplicates
  const [globalOAuthInProgress, setGlobalOAuthInProgress] = useState(false)

  useEffect(() => {
    const doAutoOAuth = async () => {
      if (TOKEN_DEBUG) {
        console.log('===== OAuth Debug Info =====')
        console.log('Skip Auth Flag:', skipAutoAuth)
        console.log('isAuthenticating State:', isAuthenticating)
        console.log('globalOAuthInProgress:', globalOAuthInProgress)
        console.log('Component mount time:', new Date(mountTime.current).toISOString())
        console.log('Current time:', new Date().toISOString())
        console.log('Time since mount (ms):', Date.now() - mountTime.current)
        console.log('Last successful validation (ms ago):', lastSuccessfulValidation.current ? Date.now() - lastSuccessfulValidation.current : 'never')
        console.log('Token validation in progress:', validationInProgress.current)
        console.log('Has Client ID:', !!GOOGLE_CLIENT_ID)
        console.log('Has Token:', !!OAUTH2_TOKEN)
        console.log('Token length (if exists):', OAUTH2_TOKEN ? OAUTH2_TOKEN.length : 0)
        console.log('Redux store settings keys:', Object.keys(settings))
        
        if (AUTH_WINDOW_DEBUG) {
          console.log('===== Auth Window Debug =====')
          console.log('Time since last validation:', lastSuccessfulValidation.current ? 
            `${(Date.now() - lastSuccessfulValidation.current) / 1000} seconds ago` : 'never validated')
        }
        
        // Check browser storage to see if token might be stored elsewhere
        try {
          const localStorageKeys = Object.keys(localStorage)
          console.log('localStorage keys:', localStorageKeys)
          
          // Check session storage too
          const sessionStorageKeys = Object.keys(sessionStorage)
          console.log('sessionStorage keys:', sessionStorageKeys)
          
          // Check if there's any redux-persist items
          const persistKeys = localStorageKeys.filter(key => key.includes('persist'))
          if (persistKeys.length > 0) {
            console.log('Redux persist keys found:', persistKeys)
            
            // Try to inspect persist:root if it exists
            try {
              const persistRoot = localStorage.getItem('persist:root')
              if (persistRoot) {
                const parsedRoot = JSON.parse(persistRoot)
                console.log('persist:root keys:', Object.keys(parsedRoot))
                
                // Check if assistant data exists and contains token
                if (parsedRoot.assistant) {
                  const assistant = JSON.parse(parsedRoot.assistant)
                  console.log('Assistant state contains settings:', !!assistant.settings)
                  if (assistant.settings?.oauth2_token) {
                    console.log('OAuth token found in persist storage:', !!assistant.settings.oauth2_token.value)
                  }
                }
              }
            } catch (parseError) {
              console.log('Error parsing persist:root:', parseError)
            }
          }
        } catch (e) {
          console.log('Error checking storage:', e)
        }
      }

      // Skip if requested, or if we already have a valid token, or if another OAuth flow is in progress
      if (skipAutoAuth || isAuthenticating || globalOAuthInProgress) {
        TOKEN_DEBUG && console.log('Skipping OAuth flow due to flags')
        return
      }
      
      // Check if we recently validated the token (in the last 5 minutes)
      const VALIDATION_CACHE_TIME = 5 * 60 * 1000; // 5 minutes in milliseconds
      if (lastSuccessfulValidation.current > 0 && 
          (Date.now() - lastSuccessfulValidation.current) < VALIDATION_CACHE_TIME) {
        TOKEN_DEBUG && console.log('Using cached token validation from', 
          (Date.now() - lastSuccessfulValidation.current) / 1000, 'seconds ago')
        return
      }
      
      // If another validation is in progress, skip starting a new one
      if (validationInProgress.current) {
        TOKEN_DEBUG && console.log('Token validation already in progress, skipping')
        return
      }

      // Check if we have a client ID
      if (GOOGLE_CLIENT_ID) {
        try {
          // First check if we have a token
          if (OAUTH2_TOKEN) {
            try {
              TOKEN_DEBUG && console.log('Validating existing token...')
              // Mark validation as in progress
              validationInProgress.current = true
              
              // Validate existing token
              const tokenInfo = await fetch(`https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=${OAUTH2_TOKEN}`)
              TOKEN_DEBUG && console.log('Token validation status:', tokenInfo.status)
              
              if (tokenInfo.ok) {
                const tokenDetails = await tokenInfo.json()
                TOKEN_DEBUG && console.log('Token is valid. Expires in:', tokenDetails.expires_in, 'seconds')
                TOKEN_DEBUG && console.log('Token scopes:', tokenDetails.scope)
                
                // Check if we have the required scopes
                const hasRequiredScopes = tokenDetails.scope && 
                  tokenDetails.scope.includes('https://www.googleapis.com/auth/cloud-platform')
                
                TOKEN_DEBUG && console.log('Has required scopes:', hasRequiredScopes)
                
                if (hasRequiredScopes) {
                  // Update last successful validation timestamp
                  lastSuccessfulValidation.current = Date.now()
                  validationInProgress.current = false
                  
                  TOKEN_DEBUG && console.log('Using existing valid token with required scopes')
                  return // Don't open OAuth window if token is valid with required scopes
                } else {
                  TOKEN_DEBUG && console.log('Token is valid but missing required scopes')
                }
              } else {
                const errorBody = await tokenInfo.text()
                TOKEN_DEBUG && console.log('Token validation error details:', errorBody)
                console.log('Existing token is invalid, will refresh')
              }
            } catch (tokenError) {
              console.log('Error validating token, will refresh:', tokenError)
            } finally {
              validationInProgress.current = false
            }
          } else {
            TOKEN_DEBUG && console.log('No token found in settings, starting OAuth flow')
          }

          console.log('Starting automatic OAuth flow')
          setIsAuthenticating(true)
          setGlobalOAuthInProgress(true)

          TOKEN_DEBUG && console.log('Calling extensionSDK.oauth2Authenticate')
          const response = await extensionSDK.oauth2Authenticate(
            'https://accounts.google.com/o/oauth2/v2/auth',
            {
              client_id: GOOGLE_CLIENT_ID,
              scope: GOOGLE_SCOPES,
              response_type: 'token',
            }
          )

          TOKEN_DEBUG && console.log('OAuth authentication completed, response received')
          const { access_token } = response
          if (access_token) {
            TOKEN_DEBUG && console.log('Received new access token, length:', access_token.length)
            dispatch(setSetting({ id: 'oauth2_token', value: access_token }))
            console.log('OAuth token automatically obtained')
            
            // Set as successful validation
            lastSuccessfulValidation.current = Date.now()
            
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
          }
        } catch (error) {
          console.error('Automatic OAuth authentication failed:', error)
        } finally {
          setIsAuthenticating(false)
          setGlobalOAuthInProgress(false)
        }
      } else {
        TOKEN_DEBUG && console.log('No Google Client ID configured, skipping OAuth')
      }
    }

    doAutoOAuth()

    // Cleanup function that runs when the component unmounts
    return () => {
      if (TOKEN_DEBUG) {
        console.log('===== useAutoOAuth unmounting =====')
        console.log('Component was mounted for:', (Date.now() - mountTime.current) / 1000, 'seconds')
        console.log('Last successful validation was:', lastSuccessfulValidation.current ? 
          new Date(lastSuccessfulValidation.current).toISOString() : 'never')
      }
    }
  }, [GOOGLE_CLIENT_ID, OAUTH2_TOKEN, extensionSDK, dispatch, skipAutoAuth, isAuthenticating, globalOAuthInProgress])

  return { isAuthenticating }
}