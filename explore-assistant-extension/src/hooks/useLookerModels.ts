import { useContext, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  setExploreMetadataById,
  ExploreMetadata,
} from '../slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { RootState } from '../store'

export const useLookerModels = () => {
  const dispatch = useDispatch()
  const { core40SDK } = useContext(ExtensionContext)
  const exploreExamplesById = useSelector(
    (state: RootState) => state.assistant.exploreExamplesById,
  )

  useEffect(() => {
    if (Object.keys(exploreExamplesById).length === 0) {
      return
    }

    const getModelsFromExploreIds = (exploreExamplesById: {
      [exploreId: string]: any
    }) => {
      const models = Object.keys(exploreExamplesById).map(
        (exploreId) => exploreId.split('/')[0],
      )
      return Array.from(new Set(models)) // Get distinct models
    }

    const models = getModelsFromExploreIds(exploreExamplesById)

    const fetchExploreMetadata = async () => {
      try {
        const metadataById: { [exploreId: string]: ExploreMetadata } = {}

        for (const model of models) {
          const lookmlModel = await core40SDK.ok(core40SDK.lookml_model(model))

          if (lookmlModel.explores) {
            lookmlModel.explores.forEach((explore: any) => {
              const { name, description, label } = explore
              const exploreId = `${model}/${name}`

              if (exploreExamplesById[exploreId]) {
                // Filter out explores not defined in exploreExamplesById
                metadataById[`${model}:${name}`] = { description, label }
              }
            })
          }
        }

        dispatch(setExploreMetadataById(metadataById))
      } catch (error) {
        console.error('Error fetching explore metadata:', error)
      }
    }

    fetchExploreMetadata()
  }, [core40SDK, dispatch, exploreExamplesById])
}
