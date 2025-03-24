import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  AssistantState,
  resetChat,
  setIsChatMode,
  setQuery,
  newThreadState,
  resetChatNoNewThread
} from '../slices/assistantSlice'
import { RootState } from '../store'
import useDropTempThread from '../hooks/useDropTempThread'


const SamplePrompts = () => {
  const dispatch = useDispatch()
  const {
    currentExplore: { modelName, exploreId },
    examples: { exploreSamples },
    me
  } = useSelector((state: RootState) => state.assistant as AssistantState)

  const samples = exploreSamples[`${modelName}:${exploreId}`]
  // make sure current thread is a valid BE generated thread
  const dropTempThread = useDropTempThread(); 


  const handleSubmit = async (prompt: string) => {
    await dropTempThread()
    dispatch(resetChatNoNewThread())
    dispatch(setQuery(prompt))
    dispatch(setIsChatMode(true))
  }

  if(!samples) return <></>

  return (
    <div className="flex flex-wrap max-w-5xl">
      {samples.map((item, index: number) => (
        <div
          className="flex flex-col w-56 min-h-44 bg-gray-200/50 hover:bg-gray-200 rounded-lg cursor-pointer text-sm p-4 m-2"
          key={index}
          onClick={() => {
            handleSubmit(item.prompt)
          }}
        >
          <div className="flex-grow font-light line-camp-5">{item.prompt}</div>
          <div className="mt-2 font-semibold justify-end">{item.category}</div>
        </div>
      ))}
    </div>
  )
}

export default SamplePrompts
