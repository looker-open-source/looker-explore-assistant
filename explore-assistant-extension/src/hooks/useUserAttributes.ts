import { useContext, useEffect, useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { 
  AssistantState, 
  setSetting,
  setUserAttributesLoaded
} from '../slices/assistantSlice'

// Debug flag for user attribute loading
const USER_ATTR_DEBUG = true

export const useUserAttributes = () => {
  const { core40SDK, extensionSDK } = useContext(ExtensionContext)
  const dispatch = useDispatch()
  
  const { settings, userAttributesLoaded } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Get the extension ID and format it for user attribute names
  const extensionId = extensionSDK?.lookerHostData?.extensionId
  const model_application = extensionId?.replace(/::/g, '_').replace(/-/g, '_').toLowerCase()

  const loadUserAttributes = async () => {
    if (isLoading || userAttributesLoaded) {
      USER_ATTR_DEBUG && console.log('User attributes already loaded or loading in progress')
      return
    }

    if (!core40SDK || !model_application) {
      USER_ATTR_DEBUG && console.log('Cannot load user attributes: missing core40SDK or model_application')
      return
    }

    try {
      setIsLoading(true)
      setError(null)
      
      USER_ATTR_DEBUG && console.log('===== Loading User Attributes =====')
      USER_ATTR_DEBUG && console.log('Model application prefix:', model_application)

      // Get user attribute values
      const myUserId = await core40SDK.ok(core40SDK.me())
      USER_ATTR_DEBUG && console.log('Current user ID:', myUserId.id)

      const userAttributeValues = await core40SDK.ok(
        core40SDK.user_attribute_user_values({
          user_id: myUserId.id || '',
          fields: "name, value, user_attribute_id",
          all_values: true
        })
      )
      
      USER_ATTR_DEBUG && console.log('Found user attributes:', userAttributeValues.length)

      let loadedCount = 0

      // Map user attribute values to their corresponding settings
      userAttributeValues.forEach((attr: any) => {
        if (attr.name && attr.name.toLowerCase().startsWith(`${model_application}_`)) {
          // Use case-insensitive matching for attribute names
          const settingKey = attr.name.toLowerCase().replace(`${model_application}_`, '')
          const value = attr.value
          
          USER_ATTR_DEBUG && console.log(`Found matching attribute: ${attr.name} -> ${settingKey} = ${value}`)
          
          // Only load specific settings that we care about
          if (
            (settingKey === 'vertex_project' || 
             settingKey === 'vertex_location' || 
             settingKey === 'vertex_model' ||
             settingKey === 'google_oauth_client_id' ||
             settingKey === 'bigquery_example_looker_model_name') && 
            value && 
            settings[settingKey]
          ) {
            dispatch(setSetting({ id: settingKey, value }))
            loadedCount++
            USER_ATTR_DEBUG && console.log(`Loaded setting from user attributes: ${settingKey}`)
          }
        }
      })

      USER_ATTR_DEBUG && console.log(`Successfully loaded ${loadedCount} settings from user attributes`)
      
      // Mark user attributes as loaded
      dispatch(setUserAttributesLoaded(true))
      
    } catch (error) {
      console.error('Error loading user attributes:', error)
      setError(error instanceof Error ? error.message : 'Failed to load user attributes')
      // Still mark as loaded to prevent infinite retries
      dispatch(setUserAttributesLoaded(true))
    } finally {
      setIsLoading(false)
    }
  }

  // Load user attributes on mount
  useEffect(() => {
    if (!userAttributesLoaded && core40SDK && model_application) {
      loadUserAttributes()
    }
  }, [core40SDK, model_application, userAttributesLoaded])

  return {
    isLoading,
    error,
    userAttributesLoaded,
    loadUserAttributes
  }
}
