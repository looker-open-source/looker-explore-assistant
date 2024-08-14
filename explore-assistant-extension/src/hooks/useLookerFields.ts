import { useContext, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  AssistantState,
  SemanticModel,
  setIsSemanticModelLoaded,
  setSemanticModels,
} from '../slices/assistantSlice'
import { RootState } from '../store'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useErrorBoundary } from 'react-error-boundary'

export const useLookerFields = () => {
  const {
    examples: { exploreSamples },
  } = useSelector((state: RootState) => state.assistant as AssistantState)

  const supportedExplores = Object.keys(exploreSamples)

  const dispatch = useDispatch()
  const { showBoundary } = useErrorBoundary()

  const { core40SDK } = useContext(ExtensionContext)

  // Load LookML metadata and provide completion status
  useEffect(() => {
    if (supportedExplores.length === 0) {
      return
    }

    const fetchSemanticModel = async (
      modelName: string,
      exploreId: string,
      exploreKey: string,
    ): Promise<SemanticModel | undefined> => {
      if (!modelName || !exploreId) {
        showBoundary({
          message: 'Default Looker Model or Explore is blank or unspecified',
        })
        return
      }

      try {
        const response = await core40SDK.ok(
          core40SDK.lookml_model_explore({
            lookml_model_name: modelName,
            explore_name: exploreId,
            fields: 'fields',
          }),
        )

        const { fields } = response

        if (!fields || !fields.dimensions || !fields.measures) {
          return undefined
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

        return {
          exploreId,
          modelName,
          exploreKey,
          dimensions,
          measures,
        }
      } catch (error) {
        showBoundary({
          message: `Failed to fetch semantic model for ${modelName}::${exploreId}`,
        })
        return undefined
      }
    }

    const loadSemanticModels = async () => {
      try {
        const fetchPromises = supportedExplores.map((exploreKey) => {
          const [modelName, exploreId] = exploreKey.split(':')
          return fetchSemanticModel(modelName, exploreId, exploreKey).then(
            (model) => ({ exploreKey, model })
          )
        })

        const results = await Promise.all(fetchPromises)
        const semanticModels: { [explore: string]: SemanticModel } = {}

        results.forEach(({ exploreKey, model }) => {
          if (model) {
            semanticModels[exploreKey] = model
          }
        })

        dispatch(setSemanticModels(semanticModels))
        dispatch(setIsSemanticModelLoaded(true))
      } catch (error) {
        showBoundary({
          message: 'Failed to load semantic models',
        })
      }
    }

    loadSemanticModels()
  }, [showBoundary, supportedExplores, core40SDK, dispatch])
}
