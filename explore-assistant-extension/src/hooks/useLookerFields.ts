import { useContext, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { setDimensions, setMeasures, setLookerFieldsLoaded } from '../slices/assistantSlice'
import { RootState } from '../store'
import { ExtensionContext } from '@looker/extension-sdk-react'
import process from 'process'
import { useErrorBoundary } from 'react-error-boundary'

export const useLookerFields = () => {
  const { exploreName, modelName } = useSelector(
    (state: RootState) => state.assistant,
  )
  const lookerModel = modelName || process.env.LOOKER_MODEL || ''
  const lookerExplore = exploreName || process.env.LOOKER_EXPLORE || ''
  const dispatch = useDispatch()
  const { showBoundary } = useErrorBoundary();

  const { core40SDK } = useContext(ExtensionContext)
  
  // load lookml metadata and provide completion status
  useEffect(() => {
    if(!lookerModel || lookerModel === '' || !lookerExplore || lookerModel === '') {
      showBoundary({message: "Default Looker Model or Explore is blank or unspecified"})
    }
    dispatch(setLookerFieldsLoaded(false))
    core40SDK
      .ok(
        core40SDK.lookml_model_explore({
          lookml_model_name: lookerModel,
          explore_name: lookerExplore,
          fields: 'fields',
        }),
      )
      .then(({ fields }) => {
        if (!fields || !fields.dimensions || !fields.measures) {
          return
        }
        const dimensions = fields.dimensions
          .filter(({ hidden }: any) => !hidden)
          .map(({ name, type, label, description, tags }: any) => ({
            name,
            type,
            label,
            description,
            tags,
          }))

        const measures = fields.measures
          .filter(({ hidden }: any) => !hidden)
          .map(({ name, type, label, description, tags }: any) => ({
            name,
            type,
            label,
            description,
            tags,
          }))

        dispatch(setDimensions(dimensions))
        dispatch(setMeasures(measures))
        dispatch(setLookerFieldsLoaded(true))
      })
      .catch((error) => {
        showBoundary(error)
        dispatch(setLookerFieldsLoaded(true))
      })
  }, [dispatch,showBoundary, modelName, exploreName]) // Dependencies array to avoid unnecessary re-executions
}
