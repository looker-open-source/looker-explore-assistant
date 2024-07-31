import React, { useCallback, useEffect, useRef, useState } from 'react'
import PromptInput from './PromptInput'
import Sidebar from './Sidebar'

import './style.css'
import SamplePrompts from '../../components/SamplePrompts'
import { ExploreEmbed } from '../../components/ExploreEmbed'
import { RootState } from '../../store'
import { useDispatch, useSelector } from 'react-redux'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import {
  addMessage,
  addPrompt,
  addToHistory,
  closeSidePanel,
  openSidePanel,
  setIsQuerying,
  setQuery,
  setSidePanelExploreUrl,
  updateLastHistoryEntry,
} from '../../slices/assistantSlice'
import MessageThread from './MessageThread'
import clsx from 'clsx'
import { Close } from '@material-ui/icons'
import { LinearProgress, Tooltip } from '@mui/material'

const AgentPage = () => {
  const endOfMessagesRef = useRef<HTMLDivElement>(null) // Ref for the last message
  const dispatch = useDispatch()
  const [expanded, setExpanded] = useState(false)
  const { generateExploreUrl, isSummarizationPrompt, summarizePrompts } =
    useSendVertexMessage()

  const {
    isChatMode,
    query,
    currentExploreThread,
    sidePanel,
    dimensions,
    measures,
    examples,
  } = useSelector((state: RootState) => state.assistant)

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

    if (!promptSummary) {
      dispatch(setIsQuerying(false))
      return
    }

    // update the history of the current thread
    if(currentExploreThread.messages.length > 0) {
      // edit existing
      dispatch(updateLastHistoryEntry(promptSummary))
    } else {
      // create new
      dispatch(addToHistory(promptSummary))
    }

    const newExploreUrl = await generateExploreUrl(promptSummary)
    dispatch(setIsQuerying(false))
    dispatch(setQuery(''))

    if (isSummary) {
      dispatch(
        addMessage({
          exploreUrl: newExploreUrl,
          actor: 'system',
          createdAt: Date.now(),
          type: 'summarize',
        }),
      )
    } else {
      dispatch(setSidePanelExploreUrl(newExploreUrl))
      dispatch(openSidePanel())

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

    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [query])

  const toggleDrawer = () => {
    setExpanded(!expanded)
  }

  const isAgentReady =
    dimensions.length > 0 &&
    measures.length > 0 &&
    examples.exploreGenerationExamples.length > 0 &&
    examples.exploreRefinementExamples.length > 0

  if (!isAgentReady) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="flex flex-col space-y-4 mx-auto max-w-2xl p-4">
          <h1 className="text-5xl font-bold">
            <span className="bg-clip-text text-transparent  bg-gradient-to-r from-pink-500 to-violet-500">
              Hello.
            </span>
          </h1>
          <h1 className="text-3xl text-gray-400">Getting everything ready...</h1>
          <div className="max-w-2xl text-blue-300">
            <LinearProgress color="inherit" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="relative page-container flex h-screen">
      <Sidebar expanded={expanded} toggleDrawer={toggleDrawer} />

      <main
        className={`flex-grow flex flex-col transition-all duration-300 ${
          expanded ? 'ml-80' : 'ml-16'
        } h-screen`}
      >
        <div className="flex-grow">
          {isChatMode ? (
            <div className="relative flex flex-row h-screen px-4 pt-4 ">
              <div
                className={clsx(
                  'flex flex-col relative',
                  sidePanel.isSidePanelOpen ? 'w-2/5' : 'w-full',
                )}
              >
                <div className="flex-grow overflow-y-auto max-h-full mb-36">
                  <div className="max-w-4xl mx-auto">
                    <MessageThread />
                  </div>
                </div>
                <div
                  className={`absolute bottom-0 left-1/2 transform -translate-x-1/2 w-4/5  transition-all duration-300 ease-in-out`}
                >
                  <PromptInput />
                </div>
              </div>

              <div
                className={clsx(
                  'flex-grow flex flex-col pb-2 pl-2 transition-all duration-300 ease-in-out transform max-w-0',
                  sidePanel.isSidePanelOpen
                    ? 'max-w-full translate-x-0 opacity-100'
                    : 'translate-x-full opacity-0',
                )}
              >
                <div className="flex flex-row bg-gray-400 text-white rounded-t-lg px-4 py-2 text-sm">
                  <div className="flex-grow">Explore</div>
                  <div className="">
                    <Tooltip title="Close Explore" placement="bottom" arrow>
                      <button
                        onClick={() => dispatch(closeSidePanel())}
                        className="text-white hover:text-gray-300"
                      >
                        <Close />
                      </button>
                    </Tooltip>
                  </div>
                </div>
                <div className="bg-gray-200 border-l-2 border-r-2 border-gray-400 flex-grow">
                  <ExploreEmbed exploreUrl={sidePanel.exploreUrl} />
                </div>
                <div className="bg-gray-400 text-white px-4 py-2 text-sm rounded-b-lg"></div>
              </div>
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

              <div
                className={`fixed bottom-0 left-1/2 transform -translate-x-1/2 w-4/5 transition-all duration-300 ease-in-out
                            ${expanded ? 'pl-80' : ''} `}
              >
                <PromptInput />
              </div>
            </>
          )}
        </div>
        <div ref={endOfMessagesRef} /> {/* Ref for the last message */}
      </main>
    </div>
  )
}

export default AgentPage
