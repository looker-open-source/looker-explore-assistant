import { useContext, useEffect, useState } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { 
  AssistantState, 
  setSetting,
  setUserAttributesLoaded
} from '../slices/assistantSlice'

// Debug flag for extension context loading
const CONTEXT_DEBUG = true

export const useExtensionContext = () => {
  const { extensionSDK, core40SDK } = useContext(ExtensionContext)
  const dispatch = useDispatch()
  
  const { settings, userAttributesLoaded } = useSelector(
    (state: RootState) => state.assistant as AssistantState,
  )
  
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadExtensionContext = async () => {
    if (isLoading || userAttributesLoaded) {
      CONTEXT_DEBUG && console.log('Extension context already loaded or loading in progress')
      return
    }

    if (!extensionSDK) {
      CONTEXT_DEBUG && console.log('Cannot load extension context: missing extensionSDK')
      return
    }
    try {
      setIsLoading(true)
      setError(null)
      CONTEXT_DEBUG && console.log('===== Loading Extension Context =====')

      // Get extension context data
      const contextData = await extensionSDK.getContextData()
      CONTEXT_DEBUG && console.log('Extension context data:', contextData)

      let loadedCount = 0

      // Load settings from context data
      const settingsToLoad = [
        'google_oauth_client_id',
        'bigquery_example_looker_model_name',
        'cloud_run_service_url',
        'vertex_model',
        'external_connection_using_oauth'
      ]

      settingsToLoad.forEach(settingKey => {
        if (contextData && contextData[settingKey] && settings[settingKey]) {
          dispatch(setSetting({ id: settingKey, value: contextData[settingKey] }))
          loadedCount++
          CONTEXT_DEBUG && console.log(`Loaded setting from context: ${settingKey} = ${contextData[settingKey]}`)
        }
      })

      CONTEXT_DEBUG && console.log(`Successfully loaded ${loadedCount} settings from extension context`)
      
      // Mark context as loaded (reusing the existing flag name for consistency)
      dispatch(setUserAttributesLoaded(true))
      
    } catch (error) {
      console.error('Error loading extension context:', error)
      setError(error instanceof Error ? error.message : 'Failed to load extension context')
      // Still mark as loaded to prevent infinite retries
      dispatch(setUserAttributesLoaded(true))
    } finally {
      setIsLoading(false)
    }
  }

  const saveExtensionContext = async (settingsToSave: Record<string, any>) => {
    if (!extensionSDK) {
      throw new Error('Extension SDK not available')
    }

    try {
      CONTEXT_DEBUG && console.log('Saving settings to extension context:', settingsToSave)
      
      // Get current context data
      let contextData = await extensionSDK.getContextData() || {}
      
      // Update with new settings
      contextData = { ...contextData, ...settingsToSave }
      
      // Save back to extension context
      await extensionSDK.saveContextData(contextData)
      
      CONTEXT_DEBUG && console.log('Successfully saved to extension context')
      return true
    } catch (error) {
      console.error('Error saving to extension context:', error)
      throw error
    }
  }

  // Load extension context on mount
  useEffect(() => {
    if (!userAttributesLoaded && extensionSDK) {
      loadExtensionContext()
    }
  }, [extensionSDK])

  return {
    isLoading,
    error,
    contextLoaded: userAttributesLoaded, // Keep same interface
    loadExtensionContext,
    saveExtensionContext
  }
}
