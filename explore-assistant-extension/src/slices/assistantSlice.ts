import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit'
import { v4 as uuidv4 } from 'uuid'
import { RootState } from '../store';
import process from 'process';

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


export const fetchUserThreads = createAsyncThunk(
  'assistant/fetchUserThreads',
  async ({ limit = 15, offset = 0 }: { limit?: number, offset?: number } = {}, { getState, dispatch }) => {
    const state = getState() as RootState;
    const { access_token } = state.auth;
    const { me } = state.assistant;
    const VERTEX_AI_ENDPOINT = process.env.VERTEX_AI_ENDPOINT || '';

    if (!me || !access_token) {
      throw new Error('User not authenticated');
    }

    try {
      // Build URL with query parameters
      const url = new URL(`${VERTEX_AI_ENDPOINT}/user/thread`);
      url.searchParams.append('user_id', me.id);
      url.searchParams.append('limit', limit.toString());
      url.searchParams.append('offset', offset.toString());

      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${access_token}`,
        },
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Server responded with ${response.status}: ${error}`);
      }

      const data = await response.json();
      // The response format from the backend is different from what we expect
      // We need to map the backend fields to frontend fields
      const threads = data.threads.map(thread => ({
        uuid: thread.thread_id.toString(),
        userId: thread.user_id,
        exploreKey: thread.explore_key || '',
        exploreId: thread.explore_id || '',
        modelName: thread.model_name || '',
        exploreUrl: thread.explore_url || '',
        summarizedPrompt: thread.summarized_prompt || '',
        promptList: thread.prompt_list || [],
        createdAt: new Date(thread.created_at).getTime(),
        messages: [] // Will be populated when user clicks on thread
      }));
    
      return {
        threads,
        totalCount: data.total_count,
        offset,
        limit
      };
    } catch (error) {
      console.error('Error fetching user threads:', error);
      return []; // Return empty array on error to avoid breaking the UI
    }
  }
);

export const fetchThreadMessages = createAsyncThunk(
  'assistant/fetchThreadMessages',
  async ({ 
    threadId, 
    limit = 2, 
    offset = 0 
  }: { 
    threadId: string, 
    limit?: number, 
    offset?: number 
  }, { getState }) => {
    const state = getState() as RootState;
    const { access_token } = state.auth;
    const VERTEX_AI_ENDPOINT = process.env.VERTEX_AI_ENDPOINT || '';

    if (!access_token) {
      throw new Error('User not authenticated');
    }

    try {
      // Build URL with query parameters
      const url = new URL(`${VERTEX_AI_ENDPOINT}/thread/${threadId}/messages`);
      url.searchParams.append('limit', limit.toString());
      url.searchParams.append('offset', offset.toString());

      const response = await fetch(url.toString(), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${access_token}`,
        },
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Server responded with ${response.status}: ${error}`);
      }

      const data = await response.json();
      
      // Map backend message format to frontend message format
      const messages = data.messages.map(message => {
        // Base message properties
        const baseMessage = {
          uuid: message.message_id.toString(),
          createdAt: new Date(message.created_at).getTime(),
          actor: message.actor,
        };

        // Based on message type, create the appropriate message object
        if (message.type === 'text') {
          return {
            ...baseMessage,
            message: message.message || '',
            type: 'text',
          } as Message;
        } else if (message.type === 'explore') {
          return {
            ...baseMessage,
            exploreUrl: message.explore_url || '',
            summarizedPrompt: message.summarized_prompt || '',
            type: 'explore',
          } as ExploreMessage;
        } else if (message.type === 'summarize') {
          return {
            ...baseMessage,
            exploreUrl: message.explore_url || '',
            summary: message.summary || '',
            type: 'summarize',
          } as SummarizeMesage;
        } else {
          // Default case for system messages without a specific type
          return {
            ...baseMessage,
            message: message.contents || '',
            type: 'text',
          } as Message;
        }
      });

      return {
        threadId,
        messages,
        totalCount: data.total_count,
        offset,
        limit,
        hasMore: messages.length >= limit
      };
    } catch (error) {
      console.error(`Error fetching messages for thread ${threadId}:`, error);
      return { 
        threadId, 
        messages: [],
        totalCount: 0,
        offset,
        limit,
        hasMore: false
      };
    }
  }
);
// Add a mapping object to define the field name conversions
const threadFieldMapping = {
  // FE field name: BE field name
  uuid: 'thread_id',
  userId: 'user_id',
  exploreKey: 'explore_key',
  exploreId: 'explore_id',
  modelName: 'model_name',
  messages: 'messages',
  exploreUrl: 'explore_url',
  summarizedPrompt: 'summarized_prompt',
  promptList: 'prompt_list',
  createdAt: 'created_at'
};

// Add a helper function to convert FE field names to BE field names
const mapThreadFieldsToBE = (threadData: Partial<ExploreThread>): Record<string, any> => {
  const mappedData: Record<string, any> = {};
  
  // Loop through each key in the thread data
  Object.entries(threadData).forEach(([feKey, value]) => {
    
    // Find the corresponding BE key from the mapping
    const beKey = threadFieldMapping[feKey as keyof typeof threadFieldMapping];
    
    if (beKey) {
      mappedData[beKey] = value;
    } else {
      // If no mapping exists, use the original key (fallback)
      mappedData[feKey] = value;
    }
  });
  
  return mappedData;
};

// Wrapper around updateCurrentThread to update local redux AND update BE thread meta
// The updated thunk with field mapping
export const updateCurrentThreadWithSync = createAsyncThunk(
  'assistant/updateCurrentThreadWithSync',
  async (threadUpdate: Partial<ExploreThread>, { dispatch, getState }) => {
    // First, update the state
    dispatch(updateCurrentThread(threadUpdate));
    
    // Then, send the update to the backend
    const state = getState() as RootState;
    const { access_token } = state.auth;
    const { currentExploreThread, me } = state.assistant;
    const VERTEX_AI_ENDPOINT = process.env.VERTEX_AI_ENDPOINT || '';
    
    if (!currentExploreThread || !me || !access_token) {
      throw new Error('Missing required data for thread update');
    }
    
    try {
      // Map the thread fields to backend naming convention
      const mappedThreadData = mapThreadFieldsToBE({
        uuid: currentExploreThread.uuid,
        userId: me.id,
        ...threadUpdate
      });
      
      // Send the PUT request
      const response = await fetch(`${VERTEX_AI_ENDPOINT}/thread/update`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${access_token}`,
        },
        body: JSON.stringify(mappedThreadData),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Server responded with ${response.status}: ${error}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error updating thread on backend:', error);
      throw error;
    }
  }
);

export const softDeleteSpecificThreads = createAsyncThunk(
  'assistant/softDeleteSpecificThreads',
  async (threadIds: number[], { getState }) => {
    const state = getState() as RootState;
    const { access_token } = state.auth;
    const { me } = state.assistant;
    const VERTEX_AI_ENDPOINT = process.env.VERTEX_AI_ENDPOINT || '';

    if (!me || !access_token) {
      throw new Error('User not authenticated');
    }

    try {
      const response = await fetch(`${VERTEX_AI_ENDPOINT}/threads/delete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${access_token}`,
        },
        body: JSON.stringify({
          user_id: me.id,
          thread_ids: threadIds
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Server responded with ${response.status}: ${error}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Error soft deleting threads:', error);
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
  // added loading state to wait for async fetchthread history
  isLoadingThreads: boolean;
  messageFetchStatus: {
    [threadId: string]: 'idle' | 'pending' | 'fulfilled' | 'rejected'
  };
  isUpdatingThread: boolean;  
  threadsInitialized: boolean;
  // pagination
  pagination: {
    threads: {
      limit: number;
      offset: number;
      hasMore: boolean;
      totalCount: number;
    },
    messages: {
      [threadId: string]: {
        limit: number;
        offset: number;
        hasMore: boolean;
        totalCount: number;
      }
    }
  }
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
  isLoadingThreads: false,
  messageFetchStatus: {},
  isUpdatingThread: false,
  threadsInitialized: false,  
  pagination: {
    threads: {
      limit: 15,
      offset: 0,
      hasMore: true,
      totalCount: 0
    },
    messages: {}
  },
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
  isSemanticModelLoaded: false,
  isLoadingThreads: false,
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
    clearHistory: (state) => {
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
    },
    // pagination
    resetThreadPagination: (state) => {
      state.pagination.threads = {
        limit: 15,
        offset: 0,
        hasMore: true,
        totalCount: 0
      };
    },
    
    resetMessagePagination: (state, action: PayloadAction<string>) => {
      const threadId = action.payload;
      state.pagination.messages[threadId] = {
        limit: 10,
        offset: 0,
        hasMore: true,
        totalCount: 0
      };
    }, 
    resetThreadHasMore: (state) => {
      state.pagination.threads.hasMore = false
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
    // Thread fetching
    builder.addCase(fetchUserThreads.pending, (state) => {
      state.isLoadingThreads = true;
    });
    builder.addCase(fetchUserThreads.fulfilled, (state, action) => {
      state.history = action.payload.threads || [];
      state.threadsInitialized = true; // Mark as initialized regardless of result
      state.isLoadingThreads = false;
      const { threads, totalCount, offset, limit } = action.payload;

      // Update pagination info
      state.pagination.threads = {
        limit,
        offset: offset + threads.length,
        hasMore: offset + threads.length < totalCount,
        totalCount
      };

      // If this is the first page (offset=0), replace history
      // Otherwise append to existing history
      if (offset === 0) {
        state.history = threads;
      } else {
        // Create a map of existing threads to avoid duplicates
        const existingThreadsMap = state.history.reduce((map, thread) => {
          map[thread.uuid] = thread;
          return map;
        }, {} as Record<string, ExploreThread>);

        // Add only new threads
        threads.forEach(thread => {
          if (!existingThreadsMap[thread.uuid]) {
            state.history.push(thread);
          }
        });
      }
      
      // Sort by creation time
      state.history = [...state.history].sort((a, b) => b.createdAt - a.createdAt);
    });
    builder.addCase(fetchUserThreads.rejected, (state) => {
      state.isLoadingThreads = false;
      state.threadsInitialized = true;
    });

    // Message fetching status tracking
    builder.addCase(fetchThreadMessages.pending, (state, action) => {
      const threadId = action.meta.arg;
      state.messageFetchStatus[threadId] = 'pending';
    });

    builder.addCase(fetchThreadMessages.fulfilled, (state, action) => {
      const { threadId, messages, totalCount, offset, limit, hasMore } = action.payload;
      state.messageFetchStatus[threadId] = 'fulfilled';

      // Update pagination info for this thread
      state.pagination.messages[threadId] = {
        limit,
        offset: offset + messages.length,
        hasMore,
        totalCount
      };

      // Find the thread in history
      const threadInHistory = state.history.find(thread => thread.uuid === threadId);
      
      if (threadInHistory) {
        // If this is the first page (offset=0), replace messages
        // Otherwise append to existing messages
        if (offset === 0) {
          threadInHistory.messages = messages;
        } else {
          // Create a map of existing messages to avoid duplicates
          const existingMessagesMap = threadInHistory.messages.reduce((map, message) => {
            map[message.uuid] = message;
            return map;
          }, {} as Record<string, ChatMessage>);

          // Add only new messages
          messages.forEach(message => {
            if (!existingMessagesMap[message.uuid]) {
              threadInHistory.messages.push(message);
            }
          });
          // Sort by creation time
          threadInHistory.messages = [...threadInHistory.messages].sort((a, b) => a.createdAt - b.createdAt);
        }
      }
      // Also update current thread if it matches
      if (state.currentExploreThread && state.currentExploreThread.uuid === threadId) {
        if (offset === 0) {
          state.currentExploreThread.messages = messages;
        } else {
          // Create a map of existing messages to avoid duplicates
          const existingMessagesMap = state.currentExploreThread.messages.reduce((map, message) => {
            map[message.uuid] = message;
            return map;
          }, {} as Record<string, ChatMessage>);

          // Add only new messages
          messages.forEach(message => {
            if (!existingMessagesMap[message.uuid]) {
              state.currentExploreThread.messages.push(message);
            }
          });
          // Sort by creation time
          state.currentExploreThread.messages = [...state.currentExploreThread.messages].sort(
            (a, b) => a.createdAt - b.createdAt
          );
        }
      }
    });
    builder.addCase(fetchThreadMessages.rejected, (state, action) => {
      const threadId = action.meta.arg;
      state.messageFetchStatus[threadId] = 'rejected';
    });
    // for update current thread thunk
    builder.addCase(updateCurrentThreadWithSync.pending, (state) => {
      // Optionally set a loading state
      state.isUpdatingThread = true;
    });
    builder.addCase(updateCurrentThreadWithSync.fulfilled, (state) => {
      state.isUpdatingThread = false;
    });
    builder.addCase(updateCurrentThreadWithSync.rejected, (state, action) => {
      state.isUpdatingThread = false;
      // Optionally handle the error
      console.error('Failed to update thread on backend:', action.error);
    });
    builder.addCase(softDeleteSpecificThreads.fulfilled, (state) => {
      // Clear the history in the frontend state
      state.history = [];
      // Reset pagination
      state.pagination.threads = {
        limit: 15,
        offset: 0,
        hasMore: true,
        totalCount: 0
      };
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

  resetThreadPagination,
  resetMessagePagination,
  resetThreadHasMore
} = assistantSlice.actions

export default assistantSlice.reducer
