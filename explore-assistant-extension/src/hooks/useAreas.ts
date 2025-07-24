import { useContext, useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useErrorBoundary } from 'react-error-boundary'
import { RootState } from '../store'
import {
  setAvailableAreas,
  setIsAreasLoaded,
  AssistantState,
  Area
} from '../slices/assistantSlice'

export const useAreas = () => {
  const dispatch = useDispatch()
  const { showBoundary } = useErrorBoundary()
  const { isAreasLoaded, settings } = useSelector((state: RootState) => state.assistant as AssistantState)
  
  const { core40SDK, lookerHostData } = useContext(ExtensionContext)
  const defaultModelName = lookerHostData?.extensionId.split('::')[0]
  
  // Use the setting if available, otherwise fallback to the default model name from extensionId
  const modelName = settings?.bigquery_example_looker_model_name?.value 
    ? String(settings.bigquery_example_looker_model_name.value)
    : defaultModelName

  const runAreasQuery = async () => {
    try {
      const query = await core40SDK.ok(
        core40SDK.run_inline_query({
          result_format: 'json',
          body: {
            model: modelName || "explore_assistant",
            view: "areas", // This will be the new view/explore for areas
            fields: [`areas.area`, `areas.explore_key`],
          }
        })
      )

      if (query === undefined) {
        return []
      }
      return query
    } catch (error: any) {
      if (error.name === 'LookerSDKError' || error.message === 'Model Not Found') {
        console.error('Error running areas query:', error.message)
        return []
      }

      // Detect OAuth-related errors and surface a user-friendly message
      if (error.message && error.message.includes('OAuth')) {
        console.error('OAuth error detected in areas query:', error.message)
        dispatch(setIsAreasLoaded(false))
        return []
      }

      console.error('Unexpected error in areas query:', error)
      showBoundary(error)
      throw new Error('error')
    }
  }

  const getAreas = async () => {
    try {
      const response = await runAreasQuery()
      
      // Better check for empty responses
      if (!response || !Array.isArray(response) || response.length === 0) {
        dispatch(setIsAreasLoaded(false))
        return
      }
      
      // Group explore_keys by area
      const areasMap: Record<string, string[]> = {}
      
      response.forEach((row: any) => {
        try {
          const area = row['areas.area']
          const exploreKey = row['areas.explore_key']
          
          if (!area || !exploreKey) {
            console.error('Missing area or explore_key in response row', row)
            return
          }
          
          if (!areasMap[area]) {
            areasMap[area] = []
          }
          
          // Add explore_key if not already present
          if (!areasMap[area].includes(exploreKey)) {
            areasMap[area].push(exploreKey)
          }
        } catch (err) {
          console.error('Error processing areas row:', err, row)
        }
      })
      
      // Convert to Area array
      const areas: Area[] = Object.entries(areasMap).map(([area, explore_keys]) => ({
        area,
        explore_keys
      }))
      
      console.log('Processed areas:', areas)
      
      // Set the data in Redux
      dispatch(setAvailableAreas(areas))
      dispatch(setIsAreasLoaded(true))
      
    } catch (error) {
      console.error('Error in getAreas:', error)
      dispatch(setIsAreasLoaded(false))
      showBoundary(error)
    }
  }

  // Create refs to track state between renders
  const hasFetched = useRef(false)
  const isFetching = useRef(false)
  const lastModelName = useRef<string | null>(null)

  // Fetch areas on component mount
  useEffect(() => {
    // Synchronously block duplicate fetches at the very top
    if (isFetching.current) {
      console.log('Areas fetch already in progress, skipping')
      return
    }
    if (isAreasLoaded) {
      return
    }
    isFetching.current = true
    console.log('Areas fetch effect triggered', {
      modelName,
      isAreasLoaded,
      hasFetched: hasFetched.current,
      isFetching: isFetching.current
    })

    // Check if model name changed since last fetch
    const modelNameChanged = lastModelName.current !== null && 
                             lastModelName.current !== modelName;
    if (modelNameChanged) {
      console.log(`Model name changed from ${lastModelName.current} to ${modelName}, forcing areas re-fetch`);
      hasFetched.current = false;
      dispatch(setIsAreasLoaded(false));
    }
    lastModelName.current = modelName || null;
    let activeRequest = true

    // Add timeout in case fetch hangs
    const timeoutId = setTimeout(() => {
      console.warn('Areas fetch timeout exceeded, forcing initialization')
      if (activeRequest) {
        console.log('TIMEOUT: Setting isAreasLoaded to true')
        dispatch(setIsAreasLoaded(true))
      }
    }, 10000)

    getAreas()
      .then(() => {
        if (activeRequest) {
          clearTimeout(timeoutId)
          hasFetched.current = true
          isFetching.current = false
          console.log('SUCCESS: Setting isAreasLoaded to true')
          dispatch(setIsAreasLoaded(true))
        }
      })
      .catch((error) => {
        if (activeRequest) {
          clearTimeout(timeoutId)
          isFetching.current = false
          console.error('Failed to fetch areas:', error)
          console.log('ERROR: Setting isAreasLoaded to false')
          dispatch(setIsAreasLoaded(false))
          hasFetched.current = false
        }
      })
    return () => {
      activeRequest = false
      clearTimeout(timeoutId)
      isFetching.current = false
    }
  }, [settings?.bigquery_example_looker_model_name?.value, modelName, dispatch])

  return {
    getAreas,
  }
}
