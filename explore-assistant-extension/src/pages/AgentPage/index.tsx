import React, { useCallback, useEffect, useRef, useState, useContext } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import PromptInput from './PromptInput'
import Sidebar from './Sidebar'
import { v4 as uuidv4 } from 'uuid'

import './style.css'
import SamplePrompts from '../../components/SamplePrompts'
import { ExploreEmbed } from '../../components/ExploreEmbed'
import { RootState } from '../../store'
import { useDispatch, useSelector } from 'react-redux'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import {
  addMessage,
  AssistantState,
  closeSidePanel,
  openSidePanel,
  setCurrenExplore,
  setIsQuerying,
  setQuery,
  setSidePanelExploreUrl,
  setuserLoggedInStatus,
  updateCurrentThread,
  updateLastHistoryEntry,
  newThreadState,
  newTempThreadState,
  setCurrentThread
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
import { AuthProvider, isTokenExpired } from '../../components/Auth/AuthProvider';
import { useErrorBoundary } from 'react-error-boundary'
import { current } from '@reduxjs/toolkit'
import useSendMessageId from '../../hooks/useSendMessageId'


const VERTEX_AI_ENDPOINT = process.env.VERTEX_AI_ENDPOINT
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
  const { showBoundary } = useErrorBoundary()
  
  
  useEffect(() => {
    loginUser();

  }, []);
  
  useEffect(() => {
    if (me) {
      loginUser();
    }
  }, [me]);


  const loginUser = async () => {
    // this function is called each time the extension is reloaded.
    // the function logs the user info into the endpoint to 
    // assign / store all actions on the extension to the user id.
    try {
      const body = JSON.stringify({
        user_id: me.id,
        name: me.display_name,
        email: me.email,
      });

      // console.log('Making request to login endpoint:');
      // console.log('Endpoint:', `${VERTEX_AI_ENDPOINT}/login`);
      // console.log('Body:', JSON.parse(body));

      const response = await fetch(`${VERTEX_AI_ENDPOINT}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${access_token}`
        },
        body: body,
      });

      
      // console.log('Login successful:', responseData);
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(`Request failed: ${errorData.detail}`);
      }
        const responseData = await response.text();
        if (response.status === 200) {
          console.log('User already exists or successfully created:', responseData);
          dispatch(setuserLoggedInStatus(true));
        } else {
          console.log('Unexpected response:', responseData);
        }
      } catch (error) {
        dispatch(setuserLoggedInStatus(false));
        console.error(
          'Error logging user id to the database',
          error
        );
        showBoundary({
          message:
            'Error logging user id to the database',
            error,
        });
      }
    };

  const endOfMessagesRef = useRef<HTMLDivElement>(null) // Ref for the last message
  const dispatch = useDispatch()
  const [expanded, setExpanded] = useState(false)
  const { generateExploreUrl, isSummarizationPrompt, summarizePrompts } =
    useSendVertexMessage()

  const {
    isChatMode,
    query,
    currentExploreThread,
    currentExplore,
    sidePanel,
    examples,
    semanticModels,
    isBigQueryMetadataLoaded,
    isSemanticModelLoaded,
    userLoggedInStatus,
    me

  } = useSelector((state: RootState) => state.assistant as AssistantState)





  const explores = Object.keys(examples.exploreSamples).map((key) => {
    const exploreParts = key.split(':')
    return {
      exploreKey: key,
      modelName: exploreParts[0],
      exploreId: exploreParts[1],
    }
  })


  useEffect(() => {
    // creates a temp in-mem thread on home page.
    // this will get triggered on the loading screen. IF browser cache dont have currentExploreThread
    // rationale is id generation are now handled by the backend.
    // thus it is prerequisite to load this first
    if (!currentExploreThread) {
        // Dispatch newThreadState to create a new thread
      const thread = newTempThreadState()
      dispatch(setCurrentThread(thread))
      
    }
  }, [isDataLoaded, query]);

  const { getMessageId } = useSendMessageId();

  const submitMessage = useCallback(async () => {
    if (query === '') {
      return
    }
  

    dispatch(setIsQuerying(true))

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

    console.log('thread:', currentExploreThread)
    console.log('Prompt List: ', promptList)
    const exploreKey = currentExploreThread?.exploreKey || currentExplore.exploreKey

    // set the explore if it is not set
    if (!currentExploreThread?.modelName || !currentExploreThread?.exploreId) {
      dispatch(
        updateCurrentThread({
          exploreId: currentExplore.exploreId,
          modelName: currentExplore.modelName,
          exploreKey: currentExplore.exploreKey,
        }),
      )
    }

    // console.log('Prompt List: ', promptList)
    // console.log(currentExploreThread)
    // console.log(currentExplore)
    const userMessageId = await getMessageId(query, 'chatMessage', query, {}, true)

    dispatch(
      addMessage({
        uuid: userMessageId,
        message: query,
        actor: 'user',
        createdAt: Date.now(),
        type: 'text',
      }),
    )
    console.log('thread:', currentExploreThread)

    const [promptSummary, isSummary] = await Promise.all([
      summarizePrompts(promptList),
      isSummarizationPrompt(query),
    ])

    if (!promptSummary) {
      dispatch(setIsQuerying(false))
      return
    }
    const { dimensions, measures } = semanticModels[exploreKey]
    const exploreGenerationExamples =
      examples.exploreGenerationExamples[exploreKey]

    const newExploreUrl = await generateExploreUrl(
      promptSummary,
      dimensions,
      measures,
      exploreGenerationExamples,
    )
    console.log('New Explore URL: ', newExploreUrl)
    dispatch(setIsQuerying(false))
    dispatch(setQuery(''))

    // If the newExploreUrl is empty, do not update the current thread
    if (
      newExploreUrl === '' ||
      newExploreUrl === null ||
      newExploreUrl === undefined
    ) {
      return
    }

    dispatch(
      updateCurrentThread({
        exploreUrl: newExploreUrl,
        summarizedPrompt: promptSummary,
      }),
    )

    if (isSummary) {
      const summaryMessageId = await getMessageId(newExploreUrl, 'chatMessage', query, {}, false)
      dispatch(
        addMessage({
          uuid: summaryMessageId,
          exploreUrl: newExploreUrl,
          actor: 'system',
          createdAt: Date.now(),
          summary: '',
          type: 'summarize',
        }),
      )
    } else {
      const exploreMessageId = await getMessageId(newExploreUrl, 'chatMessage', query, {}, false)
      dispatch(setSidePanelExploreUrl(newExploreUrl))
      dispatch(openSidePanel())

      dispatch(
        addMessage({
          uuid: exploreMessageId,
          exploreUrl: newExploreUrl,
          summarizedPrompt: promptSummary,
          actor: 'system',
          createdAt: Date.now(),
          type: 'explore',
        }),
      )
    }

    // update the history with the current contents of the thread
    dispatch(updateLastHistoryEntry())
  }, [query, semanticModels, examples, currentExplore, currentExploreThread])

  const isDataLoaded = isBigQueryMetadataLoaded && isSemanticModelLoaded
  
  useEffect(() => {
    if (!query || query === '') {
      return
    }

    if (query !== '' && isDataLoaded) {
      submitMessage()
      endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [query, isDataLoaded])

  const toggleDrawer = () => {
    setExpanded(!expanded)
  }

  const handleExploreChange = (event: SelectChangeEvent) => {
    console.log('In handleExploreChange')
    console.log(currentExploreThread)
    const exploreKey = event.target.value
    const [modelName, exploreId] = exploreKey.split(':')
    dispatch(
      setCurrenExplore({
        modelName,
        exploreId,
        exploreKey,
      }),
    )
    dispatch(
      updateCurrentThread({
        exploreId: modelName,
        modelName: exploreId,
        exploreKey: exploreKey,
      }), () => {
        console.log(currentExploreThread); // This will be logged after update finishes
      }
    )

  }

  const { access_token, expires_in } = useSelector((state: RootState) => state.auth);

  
  const isAgentReady = isBigQueryMetadataLoaded && isSemanticModelLoaded && userLoggedInStatus
  
  console.log('Agent ready state:', {
    isBigQueryMetadataLoaded,
    isSemanticModelLoaded,
    hasAccessToken: !!access_token,
    tokenExpired: isTokenExpired(access_token, expires_in),
    userLoggedInStatus: userLoggedInStatus,
});

  if (!isAgentReady) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="flex flex-col space-y-4 mx-auto max-w-2xl p-4">
          <h1 className="text-5xl font-bold">
            <span className="bg-clip-text text-transparent  bg-gradient-to-r from-pink-500 to-violet-500">
              Hello {me ? `, ${me.display_name}` : '.'}.
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
                  <div className="max-w-4xl mx-auto">
                    {!isDataLoaded ? (
                      <div className="flex flex-col space-y-4 mx-auto max-w-2xl p-4">
                        <h1 className="text-5xl font-bold">
                          <span className="bg-clip-text text-transparent  bg-gradient-to-r from-pink-500 to-violet-500">
                            Hello {me ? `, ${me.display_name}` : '.'}.
                          </span>
                        </h1>
                        <h1 className="text-3xl text-gray-400">
                          Loading the conversation and LookML Metadata...{' '}
                        </h1>
                        <div className="max-w-2xl text-blue-300">
                          <LinearProgress color="inherit" />
                        </div>
                      </div>
                    ) : (
                      <div className="pt-8">
                        <MessageThread />
                      </div>
                    )}
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
                  <ExploreEmbed
                    modelName={currentExploreThread?.modelName}
                    exploreId={currentExploreThread?.exploreId}
                    exploreUrl={sidePanel.exploreUrl}
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
                    Hello {me ? `, ${me.display_name}` : '.'}.
                  </span>
                </h1>
                <h1 className="text-5xl text-gray-400">
                  How can I help you today?
                </h1>
              </div>

              <div className="flex flex-col max-w-3xl m-auto mt-16">
                {explores.length > 1 && (
                  <div className="text-md border-b-2 p-2 max-w-3xl">
                    <FormControl className="">
                      <InputLabel>Explore</InputLabel>
                      <Select
                        value={currentExplore.exploreKey}
                        label="Explore"
                        onChange={handleExploreChange}
                      >
                        {explores.map((oneExplore) => (
                          <MenuItem
                            key={oneExplore.exploreKey}
                            value={oneExplore.exploreKey}
                          >
                            {toCamelCase(oneExplore.exploreId)}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </div>
                )}
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
