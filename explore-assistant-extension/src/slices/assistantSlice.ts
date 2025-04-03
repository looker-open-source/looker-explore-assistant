import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit'
import { v4 as uuidv4 } from 'uuid'
import { RootState } from '../store';
import process from 'process';

// TODO JOON : ENDPOINT /chat/history :  migrate chat history from in cache to cloud run endpoint.

// step 1 : create a thunk to fetch chat history from cloud run endpoint

// src/slices/assistantSlice.ts
// import { createAsyncThunk } from '@reduxjs/toolkit';
// import { RootState } from '../store';

// export const fetchChatHistory = createAsyncThunk(
//   'assistant/fetchChatHistory',
//   async (threadId: string, { getState }) => {
//     const state = getState() as RootState;
//     const access_token = state.auth.access_token;
//     const VERTEX_CF_SECRET = process.env.VERTEX_CF_SECRET || '';

//     const headers = {
//       'Content-Type': 'application/json',
//       'X-Signature': VERTEX_CF_SECRET,
//       'Authorization': `Bearer ${access_token}`,
//     };

//     const response = await fetch(`http://your-flask-server-url/chat/history`, {
//       method: 'POST',
//       headers: headers,
//       body: JSON.stringify({ contents: { user_id: threadId } }),
//     });

//     if (!response.ok) {
//       throw new Error(`Failed to fetch chat history: ${response.statusText}`);
//     }

//     return await response.json();
//   }
// );


// step 2 : Update Reducers to Handle the Fetched Data
// src/slices/assistantSlice.ts
// import { createSlice, PayloadAction } from '@reduxjs/toolkit';
// import { fetchChatHistory } from './path/to/thunks';

// const assistantSlice = createSlice({
//   name: 'assistant',
//   initialState,
//   reducers: {
//     // existing reducers
//   },
//   extraReducers: (builder) => {
//     builder.addCase(fetchChatHistory.fulfilled, (state, action) => {
//       if (state.currentExploreThread) {
//         state.currentExploreThread.messages = action.payload;
//       }
//     });
//   },
// });

// export const { /* existing actions */ } = assistantSlice.actions;
// export default assistantSlice.reducer;

// step 3 : Dispatch Fetch Action in MessageThread.tsx
// Ensure that the MessageThread component fetches chat history when it mounts.


// src/pages/AgentPage/MessageThread.tsx
// import React, { useEffect } from 'react';
// import { useSelector, useDispatch } from 'react-redux';
// import { RootState } from '../../store';
// import { fetchChatHistory } from '../../slices/assistantSlice';
// import Message from '../../components/Chat/Message';
// import ExploreMessage from '../../components/Chat/ExploreMessage';
// import SummaryMessage from '../../components/Chat/SummaryMessage';
// import { CircularProgress } from '@material-ui/core';
// import { AssistantState, ChatMessage } from '../../slices/assistantSlice';

// const MessageThread = () => {
//   const dispatch = useDispatch();
//   const { currentExploreThread, isQuerying } = useSelector(
//     (state: RootState) => state.assistant as AssistantState,
//   );

//   useEffect(() => {
//     if (currentExploreThread) {
//       dispatch(fetchChatHistory(currentExploreThread.uuid));
//     }
//   }, [currentExploreThread, dispatch]);

//   if (currentExploreThread === null) {
//     return <></>;
//   }

//   const messages = currentExploreThread.messages as ChatMessage[];

//   return (
//     <div className="">
//       {messages.map((message) => {
//         if (message.type === 'explore') {
//           return (
//             <ExploreMessage
//               key={message.uuid}
//               modelName={currentExploreThread.modelName}
//               exploreId={currentExploreThread.exploreId}
//               queryArgs={message.exploreUrl}
//               prompt={message.summarizedPrompt}
//             />
//           );
//         } else if (message.type === 'summarize') {
//           return <SummaryMessage key={message.uuid} message={message} />;
//         } else {
//           return (
//             <Message
//               key={message.uuid}
//               message={message.message}
//               actor={message.actor}
//               createdAt={message.createdAt}
//             />
//           );
//         }
//       })}
//       {isQuerying && (
//         <div className="flex flex-col text-gray-300 size-8">
//           <CircularProgress color={'inherit'} size={'inherit'} />
//         </div>
//       )}
//     </div>
//   );
// };

// export default MessageThread;

// step 4 : update the cloud run endpoint with the history of the chat

// explore-assistant-cloud-run/main.py
// from flask import Flask, request, jsonify
// import mysql.connector

// app = Flask(__name__)

// # Configure your MySQL connection
// db_config = {
//     'user': 'your-username',
//     'password': 'your-password',
//     'host': 'your-cloud-sql-instance-ip',
//     'database': 'your-database-name'
// }

// @app.route('/chat/history', methods=['POST'])
// def chat_history():
//     headers = request.headers
//     data = request.get_json()

//     # Verify headers and authorization
//     if headers.get('X-Signature') != '<VERTEX_CF_SECRET>':
//         return jsonify({'error': 'Invalid signature'}), 401

//     # Connect to MySQL
//     conn = mysql.connector.connect(**db_config)
//     cursor = conn.cursor(dictionary=True)

//     # Example: Retrieve chat history for a user
//     user_id = data['contents']['user_id']
//     query = "SELECT * FROM Messages WHERE user_id = %s ORDER BY createdAt"
//     cursor.execute(query, (user_id,))
//     chat_history = cursor.fetchall()

//     cursor.close()
//     conn.close()

//     return jsonify(chat_history)





// TODO JOON : endpoint /chat to create new chat thread
// step 1 
// **Create a New Thunk**: This should be placed in your Redux slice file, such as `assistantSlice.ts`, where other thunks and actions are defined. 
// This keeps all state management logic centralized.

// src/slices/assistantSlice.ts
// import { createAsyncThunk } from '@reduxjs/toolkit';

// export const createChatThread = createAsyncThunk(
//   'assistant/createChatThread',
//   async (threadData: { userId: string, initialMessage: string }) => {
//     const response = await fetch('http://your-server-url/chat/threads', {
//       method: 'POST',
//       headers: {
//         'Content-Type': 'application/json',
//       },
//       body: JSON.stringify(threadData),
//     });

//     if (!response.ok) {
//       throw new Error('Failed to create chat thread');
//     }

//     return await response.json();
//   }
// );


// step 2  : 
// Trigger Thread Creation: Identify the component where the user initiates a new chat thread. 
// This could be a button or form submission. 
// If this action is part of the initial app setup or a specific page, you might consider placing it in App.tsx or a dedicated component for starting new threads.

// Then, Dispatch the Thunk: Use the useDispatch hook to dispatch the createChatThread thunk. 
// This could be done in App.tsx if the thread creation is part of the app's initial setup or in a specific component where the user starts a new conversation.
// Example in App.tsx or a relevant component:

// import React from 'react';
// import { useDispatch } from 'react-redux';
// import { createChatThread } from './slices/assistantSlice';

// const StartChatComponent = () => {
//   const dispatch = useDispatch();

//   const handleStartChat = () => {
//     const threadData = {
//       userId: 'user-id', // Replace with actual user ID
//       initialMessage: 'Hello, I want to start a new chat thread.',
//     };
//     dispatch(createChatThread(threadData));
//   };

//   return (
//     <button onClick={handleStartChat}>Start New Chat</button>
//   );
// };

// export default StartChatComponent;


// Thunk to fetch UUID from /chat endpoint
export const fetchThreadId = createAsyncThunk(
  'assistant/fetchThreadId',
  async (params: { exploreKey: string, me: Object }, { getState }) => {
    if (!params.me) {
      return;
    }
    const VERTEX_AI_ENDPOINT = process.env.VERTEX_AI_ENDPOINT || '';
    const state = getState() as RootState;
    const access_token = state.auth?.access_token;
    const body = JSON.stringify({
      user_id: params.me.id,
      explore_key: params.exploreKey
    })
    try {
      const response = await fetch(`${VERTEX_AI_ENDPOINT}/thread`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${access_token}`,
        },
        body: body,
      });

      if (!response.ok || response.status !== 200) {
        const error = await response.text();
        throw new Error(`Server responded with ${response.status}: ${error}`);
      }

      const data = await response.json();
      return data.data.thread_id; // Assuming the response contains a threadId
    } catch (error) {
      console.error('Error in fetchThreadId:', error);
      throw error;
    }
  }
);




export interface Setting {
  name: string
  description: string
  value: boolean
}

export interface Settings {
  [key: string]: Setting
}

export interface ExploreSamples {
  [exploreKey: string]: Sample[]
}

export interface ExploreExamples {
  [exploreKey: string]: {
    input: string
    output: string
  }[]
}

export interface RefinementExamples {
  [exploreKey: string]: {
    input: string[]
    output: string
  }[]
}

interface Field {
  name: string
  type: string
  description: string
  tags: string[]
}

interface Sample {
  category: string
  prompt: string
}

export interface Message {
  uuid: string
  message: string
  actor: 'user' | 'system'
  createdAt: number
  type: 'text'
  intent?: 'exploreRefinement' | 'summarize' | 'dataQuestion'
}

export interface ExploreMessage {
  uuid: string
  exploreUrl: string
  actor: 'system'
  createdAt: number
  type: 'explore'
  summarizedPrompt: string
}

export interface SummarizeMesage {
  uuid: string
  exploreUrl: string
  actor: 'system'
  createdAt: number
  type: 'summarize'
  summary: string
}

export type ChatMessage = Message | ExploreMessage | SummarizeMesage

export type ExploreThread = {
  uuid: string
  exploreId: string
  modelName: string
  exploreKey: string
  messages: ChatMessage[]
  exploreUrl: string
  summarizedPrompt: string
  promptList: string[]
  createdAt: number
}


export interface SemanticModel {
  dimensions: Field[]
  measures: Field[]
  exploreKey: string
  exploreId: string
  modelName: string
}

export interface AssistantState {
  me: any
  userLoggedInStatus: boolean
  isQuerying: boolean
  isChatMode: boolean
  currentExploreThread: ExploreThread | null
  currentExplore: {
    exploreKey: string
    modelName: string
    exploreId: string
  }
  sidePanel: {
    isSidePanelOpen: boolean
    exploreUrl: string
  }
  history: ExploreThread[]
  semanticModels: {
    [exploreKey: string]: SemanticModel
  }
  query: string
  examples: {
    exploreGenerationExamples: ExploreExamples
    exploreRefinementExamples: RefinementExamples
    exploreSamples: ExploreSamples
  },
  settings: Settings,
  isBigQueryMetadataLoaded: boolean,
  isSemanticModelLoaded: boolean
}

export const newThreadState = createAsyncThunk(
  'assistant/newThreadState',
  async (me: Object | null, { dispatch, getState }) => {
    if (!me) {
      return;
    }
    const state = getState() as RootState;
    const exploreKey = state.assistant.currentExplore.exploreKey;

    try {
      if (!me) {
        return;
      }
      const threadId = await dispatch(fetchThreadId({ exploreKey, me })).unwrap();
      const thread: ExploreThread = {
        uuid: threadId,
        userId: me.id,
        exploreKey: exploreKey,
        exploreId: '',
        modelName: '',
        messages: [],
        exploreUrl: '',
        summarizedPrompt: '',
        promptList: [],
        createdAt: Date.now(),
      };
      return thread;
    } catch (error) {
      console.error('Error fetching thread ID:', error);
      // Handle error, possibly return a default thread structure
    }
  }
);

export const newTempThreadState = () => {
  // handle initial home page state
  const thread: ExploreThread = {
    uuid: 'temp',
    exploreKey: '',
    exploreId: '',
    modelName: '',
    messages: [],
    exploreUrl: '',
    summarizedPrompt: '',
    promptList: [],
    createdAt: Date.now()
  }
  return thread
};

export const initialState: AssistantState = {
  me: null,
  userLoggedInStatus: false,
  isQuerying: false,
  isChatMode: false,
  currentExploreThread: null as ExploreThread | null,
  currentExplore: {
    exploreKey: '',
    modelName: '',
    exploreId: ''
  },
  sidePanel: {
    isSidePanelOpen: false,
    exploreUrl: '',
  },
  history: [],
  query: '',
  semanticModels: {},
  examples: {
    exploreGenerationExamples: {},
    exploreRefinementExamples: {},
    exploreSamples: {}
  },
  settings: {
    show_explore_data: {
      name: 'Show Explore Data',
      description: 'By default, expand the data panel in the Explore',
      value: false,
    },
  },
  isBigQueryMetadataLoaded: false,
  isSemanticModelLoaded: false
}

export const assistantSlice = createSlice({
  name: 'assistant',
  initialState,
  reducers: {
    setMeSdk: (state, action: PayloadAction<any>) => {
      state.me = action.payload;
    },
    setuserLoggedInStatus: (state, action: PayloadAction<boolean>) => {
      state.userLoggedInStatus = action.payload;
    },
    resetExploreAssistant: () => {
      return initialState
    },
    setIsQuerying: (state, action: PayloadAction<boolean>) => {
      state.isQuerying = action.payload
    },
    setIsChatMode: (state, action: PayloadAction<boolean>) => {
      state.isChatMode = action.payload
    },
    resetChatMode: (state) => {
      state.isChatMode = false
      assistantSlice.caseReducers.resetChat(state)
    },
    resetSettings: (state) => {
      state.settings = initialState.settings
    },
    setSetting: (
      state,
      action: PayloadAction<{ id: keyof Settings; value: boolean }>,
    ) => {

      const { id, value } = action.payload
      if (state.settings[id]) {
        state.settings[id].value = value
      }
    },
    openSidePanel: (state) => {
      state.sidePanel.isSidePanelOpen = true
    },
    closeSidePanel: (state) => {
      state.sidePanel.isSidePanelOpen = false
    },
    setSidePanelExploreUrl: (state, action: PayloadAction<string>) => {
      state.sidePanel.exploreUrl = action.payload
    },
    clearHistory : (state) => {
      state.history = []
    },
    updateLastHistoryEntry: (state) => {
      if (state.currentExploreThread === null) {
        return
      }

      if (state.history.length === 0) {
        state.history.push({ ...state.currentExploreThread })
      } else {
        const currentUuid = state.currentExploreThread.uuid
        const lastHistoryUuid = state.history[state.history.length - 1].uuid
        if (currentUuid !== lastHistoryUuid) {
          state.history.push({ ...state.currentExploreThread })
        } else {
          state.history[state.history.length - 1] = state.currentExploreThread
        }
      }
    },
    setSemanticModels: (state, action: PayloadAction<AssistantState['semanticModels']>) => {
      state.semanticModels = action.payload
    },
    setExploreUrl: (state, action: PayloadAction<string>) => {
      if (state.currentExploreThread === null) {
        // state.currentExploreThread = newThreadState()
        return;
      }
      state.currentExploreThread.exploreUrl = action.payload
    },
    updateCurrentThread: (
      state,
      action: PayloadAction<Partial<ExploreThread>>,
    ) => {
      if (state.currentExploreThread === null) {
        // state.currentExploreThread = newThreadState()
        return;
      }
      state.currentExploreThread = {
        ...state.currentExploreThread,
        ...action.payload,
      }
    },
    setCurrentThread: (state, action: PayloadAction<ExploreThread>) => {
      state.currentExploreThread = { ...action.payload }
    },
    setQuery: (state, action: PayloadAction<string>) => {
      state.query = action.payload
    },
    resetChat: (state, action: PayloadAction<ExploreThread>) => {
      // state.currentExploreThread = newThreadState()
      state.currentExploreThread = action.payload;
      // state.currentExploreThread.uuid = uuidv4()
      state.currentExploreThread.exploreKey = state.currentExplore.exploreKey; // Assign the value here
      state.query = ''
      state.isChatMode = false
      state.isQuerying = false
      state.sidePanel = initialState.sidePanel
    },
    resetChatNoNewThread: (state) => {
      // patch for calls that don't create a new thread
      state.currentExploreThread.exploreKey = state.currentExplore.exploreKey; // Assign the value here
      state.query = ''
      state.isChatMode = false
      state.isQuerying = false
      state.sidePanel = initialState.sidePanel
    },
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      if (state.currentExploreThread === null) {
        // state.currentExploreThread = newThreadState()
        return;
      }
      if (action.payload.uuid === undefined) {
        action.payload.uuid = uuidv4()
      }
      state.currentExploreThread.messages.push(action.payload)
    },
    setExploreGenerationExamples(
      state,
      action: PayloadAction<AssistantState['examples']['exploreGenerationExamples']>,
    ) {
      state.examples.exploreGenerationExamples = action.payload
    },
    setExploreRefinementExamples(
      state,
      action: PayloadAction<AssistantState['examples']['exploreRefinementExamples']>,
    ) {
      state.examples.exploreRefinementExamples = action.payload
    },
    updateSummaryMessage: (
      state,
      action: PayloadAction<{ uuid: string; summary: string }>,
    ) => {
      const { uuid, summary } = action.payload
      if (state.currentExploreThread === null) {
        // state.currentExploreThread = newThreadState()
        return;
      }
      const message = state.currentExploreThread.messages.find(
        (message) => message.uuid === uuid,
      ) as SummarizeMesage
      message.summary = summary
    },
    setExploreSamples(
      state,
      action: PayloadAction<ExploreSamples>,
    ) {
      state.examples.exploreSamples = action.payload
    },
    setisBigQueryMetadataLoaded: (
      state,
      action: PayloadAction<boolean>
    ) => {
      state.isBigQueryMetadataLoaded = action.payload
    },
    setIsSemanticModelLoaded: (state, action: PayloadAction<boolean>) => {
      state.isSemanticModelLoaded = action.payload
    },
    setCurrenExplore: (state, action: PayloadAction<AssistantState['currentExplore']>) => {
      state.currentExplore = action.payload
    }
  },
  extraReducers: (builder) => {
    builder.addCase(newThreadState.fulfilled, (state, action) => {
      // Update the currentExploreThread with the new thread
      state.currentExploreThread = action.payload;
    });
    builder.addCase(fetchThreadId.fulfilled, (state, action) => {
      // Handle the fulfilled state if needed
    });
  },
})

export const {
  setuserLoggedInStatus,
  setMeSdk,

  setIsQuerying,
  setIsChatMode,
  resetChatMode,

  updateLastHistoryEntry,
  clearHistory,

  setSemanticModels,
  setIsSemanticModelLoaded,
  setExploreUrl,
  setQuery,
  resetChat,
  resetChatNoNewThread,
  addMessage,
  setExploreGenerationExamples,
  setExploreRefinementExamples,
  setExploreSamples,

  setisBigQueryMetadataLoaded,

  updateCurrentThread,
  setCurrentThread,

  openSidePanel,
  closeSidePanel,
  setSidePanelExploreUrl,

  setSetting,
  resetSettings,

  updateSummaryMessage,

  setCurrenExplore,

  resetExploreAssistant,
} = assistantSlice.actions

export default assistantSlice.reducer
