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
      lookerModel: string,
      lookerExplore: string,
    ): Promise<SemanticModel | undefined> => {
      if (!lookerModel || !lookerExplore) {
        showBoundary({
          message: 'Default Looker Model or Explore is blank or unspecified',
        })
        return
      }

      try {
        const response = await core40SDK.ok(
          core40SDK.lookml_model_explore({
            lookml_model_name: lookerModel,
            explore_name: lookerExplore,
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
          dimensions,
          measures,
        }
      } catch (error) {
        showBoundary({
          message: `Failed to fetch semantic model for ${lookerModel}::${lookerExplore}`,
        })
        return undefined
      }
    }

    const loadSemanticModels = async () => {
      try {
        const fetchPromises = supportedExplores.map((explore) => {
          const [lookerModel, lookerExplore] = explore.split('::')
          return fetchSemanticModel(lookerModel, lookerExplore).then(
            (model) => ({ explore, model })
          )
        })

        const results = await Promise.all(fetchPromises)
        const semanticModels: { [explore: string]: SemanticModel } = {}

        results.forEach(({ explore, model }) => {
          if (model) {
            semanticModels[explore] = model
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
