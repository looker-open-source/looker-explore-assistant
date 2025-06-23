import React, { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  AssistantState,
  resetChat,
  setIsChatMode,
  setQuery,
  ensureValidExploreContext,
} from '../slices/assistantSlice'
import { RootState } from '../store'

const SamplePrompts = () => {
  const dispatch = useDispatch()
  const {
    currentExplore: { modelName, exploreId, exploreKey },
    examples: { exploreSamples },
  } = useSelector((state: RootState) => state.assistant as AssistantState)

  // Ensure we have a valid explore context when component mounts
  useEffect(() => {
    if (!modelName || !exploreId || !exploreKey) {
      dispatch(ensureValidExploreContext())
    }
  }, [modelName, exploreId, exploreKey, dispatch])

  // Use exploreKey directly if available, otherwise construct from modelName:exploreId
  let currentExploreKey = exploreKey
  if (!currentExploreKey && modelName && exploreId) {
    currentExploreKey = `${modelName}:${exploreId}`
  }

  // Don't show samples if we don't have a valid explore context
  if (!currentExploreKey) {
    return (
      <div className="text-gray-500 p-4 text-center">
        <p>Please select an explore to see sample prompts</p>
      </div>
    )
  }

  const samples = exploreSamples[currentExploreKey]

  const handleSubmit = (prompt: string) => {
    // Don't reset chat completely - preserve the current explore context
    dispatch(setQuery(prompt))
    dispatch(setIsChatMode(true))
  }

  // Helper function to extract prompt text from any format
  const getPromptText = (item: any): string => {
    if (typeof item === 'string') {
      return item
    }
    if (typeof item === 'object' && item !== null) {
      // Try common property names for prompt text
      return item.prompt || item.text || item.question || item.query || item.example || JSON.stringify(item)
    }
    // Fallback to string representation
    return String(item)
  }

  // Helper function to extract category from any format
  const getCategory = (item: any): string => {
    if (typeof item === 'object' && item !== null) {
      return item.category || item.type || item.tag || 'Sample'
    }
    return 'Sample'
  }

  // Filter out invalid samples and ensure we have valid prompt text
  const validSamples = samples?.filter(item => {
    const promptText = getPromptText(item)
    return promptText && promptText.trim().length > 0
  }) || []

  if (validSamples.length === 0) return <></>

  return (
    <div className="flex flex-wrap max-w-5xl">
      {validSamples.map((item, index: number) => {
        const promptText = getPromptText(item)
        const category = getCategory(item)
        
        return (
          <div
            className="flex flex-col w-56 min-h-44 bg-gray-200/50 hover:bg-gray-200 rounded-lg cursor-pointer text-sm p-4 m-2"
            key={index}
            onClick={() => {
              handleSubmit(promptText)
            }}
          >
            <div className="flex-grow font-light line-clamp-5">{promptText}</div>
            <div className="mt-2 font-semibold justify-end">{category}</div>
          </div>
        )
      })}
    </div>
  )
}

export default SamplePrompts
