import { useContext, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../store'
import { setDimensions, setMeasures } from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'
import process from 'process'

export const useLookerFields = () => {
  const { exploreName, modelName} = useSelector(
    (state: RootState) => state.assistant,
  )
  // const lookerModel = process.env.LOOKER_MODEL || ''
  // const lookerExplore = process.env.LOOKER_EXPLORE || ''
  const dispatch = useDispatch()

  const { core40SDK } = useContext(ExtensionContext)

  useEffect(() => {
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
        const dimensions = fields.dimensions.map(
          ({ name, type, description, tags }: any) => ({
            name,
            type,
            description,
            tags,
          }),
        )

        const measures = fields.measures.map(
          ({ name, type, description, tags }: any) => ({
            name,
            type,
            description,
            tags,
          }),
        )

        dispatch(setDimensions(dimensions))
        dispatch(setMeasures(measures))
      })
  }, [dispatch, modelName, exploreName]) // Dependencies array to avoid unnecessary re-executions
}

