import { useEffect, useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { useContext } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { AssistantState, setSetting } from '../slices/assistantSlice'

export const useAutoOAuth = (skipAutoAuth = false) => {
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const { extensionSDK } = useContext(ExtensionContext)
  const dispatch = useDispatch()
  
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
      // Skip if requested, or if we already have a valid token, or if another OAuth flow is in progress
      if (skipAutoAuth || isAuthenticating || globalOAuthInProgress) {
        return
      }

      // Check if we have a client ID
      if (GOOGLE_CLIENT_ID) {
        try {
          // Validate existing token if present
          if (OAUTH2_TOKEN) {
            const tokenInfo = await fetch('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=' + OAUTH2_TOKEN)
            if (tokenInfo.ok) {
              console.log('Existing OAuth token is valid')
              return
            }
          }

          console.log('Starting automatic OAuth flow')
          setIsAuthenticating(true)
          setGlobalOAuthInProgress(true)

          const response = await extensionSDK.oauth2Authenticate(
            'https://accounts.google.com/o/oauth2/v2/auth',
            {
              client_id: GOOGLE_CLIENT_ID,
              scope: GOOGLE_SCOPES,
              response_type: 'token',
            }
          )

          const { access_token } = response
          if (access_token) {
            dispatch(setSetting({ id: 'oauth2_token', value: access_token }))
            console.log('OAuth token automatically obtained')
          }
        } catch (error) {
          console.error('Automatic OAuth authentication failed:', error)
        } finally {
          setIsAuthenticating(false)
          setGlobalOAuthInProgress(false)
        }
      }
    }

    doAutoOAuth()
  }, [GOOGLE_CLIENT_ID, OAUTH2_TOKEN, extensionSDK, dispatch, skipAutoAuth, isAuthenticating, globalOAuthInProgress])

  return { isAuthenticating }
}