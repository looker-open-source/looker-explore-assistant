import React, { useCallback, useEffect, useState } from 'react'
import PromptInput from './PromptInput'
import Sidebar from './Sidebar'

import './style.css'
import SamplePrompts from '../../components/SamplePrompts'
import { ExploreEmbed } from '../../components/ExploreEmbed'
import { RootState } from '../../store'
import { useDispatch, useSelector } from 'react-redux'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import { addMessage, addPrompt, setExploreUrl, setIsQuerying } from '../../slices/assistantSlice'
import MessageThread from './MessageThread'

const AgentPage = () => {
  const dispatch = useDispatch()
  const [expanded, setExpanded] = useState(false)
  const {
    generateExploreUrl,
    isSummarizationPrompt,
    summarizePrompts,
  } = useSendVertexMessage()

  const { isChatMode, query, currentExploreThread } = useSelector(
    (state: RootState) => state.assistant,
  )

  const submitMessage = useCallback(async () => {
    dispatch(addPrompt(query))
    dispatch(setIsQuerying(true))
    
    const promptList = [...currentExploreThread.promptList, query]

    dispatch(
      addMessage({
        message: query,
        actor: 'user',
        createdAt: Date.now(),
        type: 'text',
      }),
    )
    
    const [promptSummary, isSummary] = await Promise.all([
      summarizePrompts(promptList),
      isSummarizationPrompt(query),
    ])

    if(!promptSummary) {
      dispatch(setIsQuerying(false))
      return
    }
    const newExploreUrl = await generateExploreUrl(promptSummary)
    dispatch(setIsQuerying(false))

    if (isSummary) {
      dispatch(
        addMessage({
          exploreUrl: currentExploreThread.exploreUrl,
          actor: 'system',
          createdAt: Date.now(),
          type: 'summarize',
        }),
      )
    } else {
      dispatch(setExploreUrl(newExploreUrl))

      dispatch(
        addMessage({
          exploreUrl: newExploreUrl,
          summarizedPrompt: promptSummary,
          actor: 'system',
          createdAt: Date.now(),
          type: 'explore',
        }),
      )
    }
  }, [query])

  useEffect(() => {
    if (!query) {
      return
    }
    submitMessage()
  }, [query])

  const toggleDrawer = () => {
    setExpanded(!expanded)
  }

  return (
    <div className="relative page-container flex h-screen">
      <Sidebar expanded={expanded} toggleDrawer={toggleDrawer} />

      <main
        className={`flex-grow flex flex-col transition-all duration-300 ${
          expanded ? 'ml-80' : 'ml-16'
        } p-4 h-screen`}
      >
        <div className="flex-grow p-4 pb-36">
          {isChatMode ? (
            <div className="">
              <ExploreEmbed />
              <MessageThread  />
            </div>
          ) : (
            <>
              <div className="flex flex-col space-y-4 mx-auto max-w-2xl p-4">
                <h1 className="text-5xl font-bold">
                  <span className="bg-clip-text text-transparent  bg-gradient-to-r from-pink-500 to-violet-500">
                    Hello.
                  </span>
                </h1>
                <h1 className="text-5xl text-gray-400">
                  How can I help you today?
                </h1>
              </div>

              <div className="flex justify-center items-center mt-16">
                <SamplePrompts />
              </div>
            </>
          )}
        </div>
        <div className={`
           fixed bottom-0 left-1/2 transform -translate-x-1/2 w-4/5

          transition-all duration-300 ease-in-out

           ${expanded ? 'pl-80' : ''}
          `}>
          <PromptInput />
        </div>
      </main>
    </div>
  )
}

export default AgentPage
