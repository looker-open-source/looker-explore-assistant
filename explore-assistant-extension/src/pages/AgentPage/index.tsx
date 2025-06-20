import React, { useCallback, useEffect, useRef, useState, useContext } from 'react'
import PromptInput from './PromptInput'
import Sidebar from './Sidebar'
import { v4 as uuidv4 } from 'uuid'

import './style.css'
import SamplePrompts from '../../components/SamplePrompts'
import { ExploreEmbed } from '../../components/ExploreEmbed'
import { RootState } from '../../store'
import { useDispatch, useSelector } from 'react-redux'
import useSendCloudRunMessage from '../../hooks/useSendCloudRunMessage'
import {
  addMessage,
  AssistantState,
  closeSidePanel,
  openSidePanel,
  resetChat,
  setCurrenExplore,
  setIsQuerying,
  setQuery,
  setSidePanelExploreParams,
  updateCurrentThread,
  updateLastHistoryEntry,
} from '../../slices/assistantSlice'
import MessageThread from './MessageThread'
import clsx from 'clsx'
import { Close } from '@material-ui/icons'
import {
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  SelectChangeEvent,
  Tooltip,
} from '@mui/material'
import { getRelativeTimeString } from '../../utils/time'

const toCamelCase = (input: string): string => {
  // Remove underscores, make following letter uppercase
  let result = input.replace(
    /_([a-z])/g,
    (_match, letter) => ' ' + letter.toUpperCase(),
  )

  // Capitalize the first letter of the string
  result = result.charAt(0).toUpperCase() + result.slice(1)

  return result
}

const AgentPage = () => {
  const endOfMessagesRef = useRef<HTMLDivElement>(null) // Ref for the last message
  const dispatch = useDispatch()
  const [expanded, setExpanded] = useState(false)
  const { processPrompt } = useSendCloudRunMessage()

  const {
    isChatMode,
    query,
    isQuerying,
    currentExploreThread,
    currentExplore,
    sidePanel,
    examples,
    semanticModels,
    isBigQueryMetadataLoaded,
    isSemanticModelLoaded,
  } = useSelector((state: RootState) => state.assistant as AssistantState)

  const explores = Object.keys(examples.exploreSamples).map((key) => {
    const exploreParts = key.split(':')
    return {
      exploreKey: key,
      modelName: exploreParts[0],
      exploreId: exploreParts[1],
    }
  })

  const scrollIntoView = useCallback(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [endOfMessagesRef])

  useEffect(() => {
    scrollIntoView()
  }, [currentExploreThread, query, isQuerying])

  const submitMessage = useCallback(async () => {
    if (query === '') {
      return
    }

    dispatch(setIsQuerying(true))

    // Check if this is a new conversation
    const isNewConversation = !currentExploreThread || currentExploreThread.messages.length === 0;
    
    // Ensure we have a thread with a UUID for consistent conversation ID
    let conversationId: string
    if (currentExploreThread?.uuid) {
      conversationId = currentExploreThread.uuid
    } else {
      // Create a new thread if one doesn't exist
      conversationId = uuidv4()
      dispatch(
        updateCurrentThread({
          uuid: conversationId,
        }),
      )
    }
    
    console.log('Current thread:', currentExploreThread?.uuid ? 'exists' : 'none')
    console.log('Using conversation ID:', conversationId, 'isNewConversation:', isNewConversation)
    
    // update the prompt list
    let promptList = [query]
    if (currentExploreThread && currentExploreThread.promptList) {
      promptList = [...currentExploreThread.promptList, query]
    }

    dispatch(
      updateCurrentThread({
        promptList,
      }),
    )

    // Add user's message to the thread immediately
    dispatch(
      addMessage({
        uuid: uuidv4(),
        message: query,
        actor: 'user',
        createdAt: Date.now(),
        type: 'text',
      }),
    )
    
    try {
      // SINGLE CALL to Cloud Run service
      const response = await processPrompt(query, conversationId, promptList)
      
      console.log('Cloud Run response:', response)
      
      // Handle explore determination from response
      let exploreKey = currentExplore.exploreKey
      let modelName = currentExplore.modelName
      let exploreId = currentExplore.exploreId
      
      if (response.explore_key && response.explore_key !== exploreKey) {
        exploreKey = response.explore_key
        const [newModelName, newExploreId] = exploreKey.split(':')
        modelName = newModelName
        exploreId = newExploreId
        
        dispatch(
          setCurrenExplore({
            modelName,
            exploreId,
            exploreKey,
          })
        )
      }

      // Always update thread with current explore info
      console.log('Updating thread with modelName:', modelName, 'exploreId:', exploreId)
      dispatch(
        updateCurrentThread({
          exploreId: exploreId,
          modelName: modelName,
          exploreKey: exploreKey,
        }),
      )

      // Update thread with response data
      console.log('Updating thread with explore params:', response.explore_params)
      dispatch(
        updateCurrentThread({
          exploreParams: response.explore_params || {},
          summarizedPrompt: response.summarized_prompt || query,
        }),
      )

      // Add appropriate message based on response type
      const messageType = response.message_type || 'explore'
      
      if (messageType === 'summarize') {
        dispatch(
          addMessage({
            exploreParams: response.explore_params || {},
            uuid: uuidv4(),
            actor: 'system',
            createdAt: Date.now(),
            summary: response.summary || '',
            type: 'summarize',
          }),
        )
      } else {
        // Default to explore message
        console.log('Setting side panel explore params:', response.explore_params)
        console.log('Explore params type:', typeof response.explore_params)
        console.log('Explore params JSON:', JSON.stringify(response.explore_params, null, 2))
        
        dispatch(setSidePanelExploreParams(response.explore_params || {}))
        dispatch(openSidePanel())

        const messageExploreParams = response.explore_params || {}
        console.log('Adding message with explore params:', messageExploreParams)
        

        // export interface ExploreMessage {
        //   uuid: string
        //   exploreParams: ExploreParams
        //   actor: 'system'
        //   createdAt: number
        //   type: 'explore'
        //   summarizedPrompt: string
        // }
        dispatch(
          addMessage({
            exploreParams: messageExploreParams,
            uuid: uuidv4(),
            summarizedPrompt: response.summarized_prompt || query,
            actor: 'system',
            createdAt: Date.now(),
            type: 'explore',
          }),
        )
      }

      // scroll to bottom of message thread
      scrollIntoView()

      // update the history with the current contents of the thread
      dispatch(updateLastHistoryEntry())
      
    } catch (error) {
      console.error('Error processing prompt:', error)
      
      // Add error message
      dispatch(
        addMessage({
          uuid: uuidv4(),
          message: 'Sorry, I encountered an error processing your request. Please try again.',
          actor: 'system',
          createdAt: Date.now(),
          type: 'text',
        }),
      )
    } finally {
      dispatch(setIsQuerying(false))
      dispatch(setQuery(''))
    }
  }, [query, currentExplore, currentExploreThread, processPrompt, dispatch, scrollIntoView])

  const isDataLoaded = isBigQueryMetadataLoaded && isSemanticModelLoaded

  useEffect(() => {
    if (!query || query === '' || !isDataLoaded) {
      return
    }

    submitMessage()
    scrollIntoView()
  }, [query, isDataLoaded])

  const toggleDrawer = () => {
    setExpanded(!expanded)
  }

  const handleExploreChange = (event: SelectChangeEvent) => {
    const exploreKey = event.target.value
    const [modelName, exploreId] = exploreKey.split(':')
    
    // Update the current explore in Redux
    dispatch(
      setCurrenExplore({
        modelName,
        exploreId,
        exploreKey,
      }),
    )
    
    // Reset chat when switching explores
    if (currentExploreThread && currentExploreThread.messages.length > 0) {
      // Start a new thread for the new explore
      dispatch(resetChat());
      
      // Add a message to inform the user that the explore has changed
      dispatch(
        addMessage({
          uuid: uuidv4(),
          message: `Using the data model "${exploreId}" for this conversation.`,
          actor: 'system',
          createdAt: Date.now(),
          type: 'text',
        }),
      );
    }
  }

  const isAgentReady = isBigQueryMetadataLoaded && isSemanticModelLoaded

  console.log('agent ready?', isAgentReady, isBigQueryMetadataLoaded, isSemanticModelLoaded)
  
  if (!isAgentReady) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="flex flex-col space-y-4 mx-auto max-w-2xl p-4">
          <h1 className="text-5xl font-bold">
            <span className="bg-clip-text text-transparent  bg-gradient-to-r from-pink-500 to-violet-500">
              Hello.
            </span>
          </h1>
          <h1 className="text-3xl text-gray-400">
            Getting everything ready...
          </h1>
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
          {isChatMode && (
            <div className="z-10 flex flex-row items-start text-xs fixed inset w-full h-10 pl-2 bg-gray-50 border-b border-gray-200">
              <ol
                role="list"
                className="flex w-full max-w-screen-xl space-x-4 px-4 sm:px-6 lg:px-4"
              >
                <li className="flex">
                  <div className="flex items-center">Explore Assistant</div>
                </li>

                <li className="flex">
                  <div className="flex items-center h-10 ">
                    <svg
                      fill="currentColor"
                      viewBox="0 0 44 44"
                      preserveAspectRatio="none"
                      aria-hidden="true"
                      className="h-full w-6 flex-shrink-0 text-gray-300"
                    >
                      <path d="M.293 0l22 22-22 22h1.414l22-22-22-22H.293z" />
                    </svg>
                    <div className="ml-4 text-xs font-medium text-gray-500 hover:text-gray-700">
                      {toCamelCase(currentExploreThread?.exploreId || '')}
                    </div>
                  </div>
                </li>

                <li className="flex">
                  <div className="flex items-center h-10">
                    <svg
                      fill="currentColor"
                      viewBox="0 0 44 44"
                      preserveAspectRatio="none"
                      aria-hidden="true"
                      className="h-full w-6 flex-shrink-0 text-gray-300"
                    >
                      <path d="M.293 0l22 22-22 22h1.414l22-22-22-22H.293z" />
                    </svg>
                    <div className="ml-4 text-xs font-medium text-gray-500 hover:text-gray-700">
                      Chat (started{' '}
                      {getRelativeTimeString(
                        currentExploreThread?.createdAt
                          ? new Date(currentExploreThread.createdAt)
                          : new Date(),
                      )}
                      )
                    </div>
                  </div>
                </li>
              </ol>
            </div>
          )}
          {isChatMode ? (
            <div className="relative flex flex-row h-screen px-4 pt-6 ">
              <div
                className={clsx(
                  'flex flex-col relative',
                  sidePanel.isSidePanelOpen ? 'w-2/5' : 'w-full',
                )}
              >
                <div className="flex-grow overflow-y-auto max-h-full mb-36 ">
                  <div className="max-w-4xl mx-auto mt-8">
                    <MessageThread endOfMessageRef={endOfMessagesRef} />
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
                  'flex-grow flex flex-col pb-2 pl-2 pt-8 transition-all duration-300 ease-in-out transform max-w-0',
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
                  {console.log('Side panel rendering ExploreEmbed with:')}
                  {console.log('modelName:', currentExploreThread?.modelName)}
                  {console.log('exploreId:', currentExploreThread?.exploreId)}
                  {console.log('sidePanel.exploreParams:', sidePanel.exploreParams)}
                  {console.log('sidePanel.isSidePanelOpen:', sidePanel.isSidePanelOpen)}
                  <ExploreEmbed
                    modelName={currentExploreThread?.modelName}
                    exploreId={currentExploreThread?.exploreId}
                    exploreParams={sidePanel.exploreParams}
                  />
                </div>
                <div className="bg-gray-400 text-white px-4 py-2 text-sm rounded-b-lg"></div>
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-col space-y-4 mx-auto max-w-3xl p-4">
                <h1 className="text-5xl font-bold">
                  <span className="bg-clip-text text-transparent  bg-gradient-to-r from-pink-500 to-violet-500">
                    Hello.
                  </span>
                </h1>
                <h1 className="text-5xl text-gray-400">
                  How can I help you today?
                </h1>
              </div>

              <div className="flex flex-col max-w-3xl m-auto mt-16">
                <div className="text-md p-2 max-w-3xl">
                  <p className="text-gray-500 mb-4">
                    Just start asking questions about your data. I'll automatically select the most relevant data model for you.
                  </p>
                </div>
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
      </main>
    </div>
  )
}

export default AgentPage
