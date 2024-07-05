import { useContext, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  setDimensions,
  setMeasures,
  setExploreDimensionsById,
  setExploreMeasuresById,
} from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'
import { useErrorBoundary } from 'react-error-boundary'

export const useLookerFields = () => {
  const {
    modelName,
    exploreName,
    exploreId,
    exploreDimensionsById,
    exploreMeasuresById,
  } = useSelector((state: RootState) => state.assistant)

  const dispatch = useDispatch()
  const { showBoundary } = useErrorBoundary()

  const { core40SDK } = useContext(ExtensionContext)

  useEffect(() => {
    if (modelName && exploreName && exploreId) {
      if (
        !exploreDimensionsById[exploreId] ||
        !exploreMeasuresById[exploreId]
      ) {
        core40SDK
          .ok(
            core40SDK.lookml_model_explore({
              lookml_model_name: modelName,
              explore_name: exploreName,
              fields: 'fields',
            }),
          )
          .then(({ fields }) => {
            if (!fields || !fields.dimensions || !fields.measures) {
              return
            }

            const dimensions = fields.dimensions
              .filter(({ hidden }: any) => !hidden)
              .map(({ name, type, description, tags }: any) => ({
                name,
                type,
                description,
                tags,
              }))

            const measures = fields.measures
              .filter(({ hidden }: any) => !hidden)
              .map(({ name, type, description, tags }: any) => ({
                name,
                type,
                description,
                tags,
              }))

            // Dispatch the dimensions and measures to the store by exploreId
            dispatch(setExploreDimensionsById({ [exploreId]: dimensions }))
            dispatch(setExploreMeasuresById({ [exploreId]: measures }))
          })
          .catch((error) => {
            showBoundary(error)
          })
      } else {
        // If the entries exist in the state, use them to set the dimensions and measures
        dispatch(setDimensions(exploreDimensionsById[exploreId]))
        dispatch(setMeasures(exploreMeasuresById[exploreId]))
      }
    }
  }, [
    dispatch,
    showBoundary,
    modelName,
    exploreName,
    exploreId,
    exploreDimensionsById,
    exploreMeasuresById,
  ])
}
