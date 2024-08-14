import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import { v4 as uuidv4 } from 'uuid'

export interface Setting {
  name: string
  description: string
  value: boolean
}

export interface Settings {
  [key: string]: Setting
}

interface Field {
  name: string
  type: string
  description: string
  tags: string[]
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
  messages: ChatMessage[]
  exploreUrl: string
  summarizedPrompt: string
  promptList: string[]
}

export interface AssistantState {
  isQuerying: boolean
  isChatMode: boolean
  currentExploreThread: ExploreThread | null
  sidePanel: {
    isSidePanelOpen: boolean
    exploreUrl: string
  }
  history: ExploreThread[]
  dimensions: Field[]
  measures: Field[]
  query: string
  exploreId: string
  exploreName: string
  modelName: string
  examples: {
    exploreGenerationExamples: {
      input: string
      output: string
    }[]
    exploreRefinementExamples: {
      input: string[]
      output: string
    }[]
  }
  settings: Settings
}

export const newThreadState = () => {
  const thread: ExploreThread = {
    uuid: uuidv4(),
    messages: [],
    exploreUrl: '',
    summarizedPrompt: '',
    promptList: [],
  }
  return thread
}

export const initialState: AssistantState = {
  isQuerying: false,
  isChatMode: false,
  currentExploreThread: null,
  sidePanel: {
    isSidePanelOpen: false,
    exploreUrl: '',
  },
  history: [],
  dimensions: [],
  measures: [],
  query: '',
  exploreId: '',
  exploreName: '',
  modelName: '',
  examples: {
    exploreGenerationExamples: [],
    exploreRefinementExamples: [],
  },
  settings: {
    show_explore_data: {
      name: 'Show Explore Data',
      description: 'By default, expand the data panel in the Explore',
      value: false,
    },
  },
}

export const assistantSlice = createSlice({
  name: 'assistant',
  initialState,
  reducers: {
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
    addToHistory: (state, action: PayloadAction<ExploreThread>) => {
      state.history.push(action.payload)
    },
    clearHistory: (state) => {
      state.history = []
    },
    setDimensions: (state, action: PayloadAction<Field[]>) => {
      state.dimensions = action.payload
    },
    setMeasures: (state, action: PayloadAction<Field[]>) => {
      state.measures = action.payload
    },
    setExploreUrl: (state, action: PayloadAction<string>) => {
      if (state.currentExploreThread === null) {
        state.currentExploreThread = newThreadState()
      }
      state.currentExploreThread.exploreUrl = action.payload
    },
    updateCurrentThread: (
      state,
      action: PayloadAction<Partial<ExploreThread>>,
    ) => {
      if (state.currentExploreThread === null) {
        state.currentExploreThread = newThreadState()
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
    resetChat: (state) => {
      state.currentExploreThread = newThreadState()
      state.currentExploreThread.uuid = uuidv4()
      state.query = ''
      state.isChatMode = false
      state.isQuerying = false
      state.sidePanel = initialState.sidePanel
    },
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      if (state.currentExploreThread === null) {
        state.currentExploreThread = newThreadState()
      }
      if (action.payload.uuid === undefined) {
        action.payload.uuid = uuidv4()
      }
      state.currentExploreThread.messages.push(action.payload)
    },
    addPrompt: (state, action: PayloadAction<string>) => {
      if (state.currentExploreThread === null) {
        state.currentExploreThread = newThreadState()
      }
      state.currentExploreThread.promptList.push(action.payload)
    },
    setExploreId: (state, action: PayloadAction<string>) => {
      state.exploreId = action.payload
    },
    setExploreName: (state, action: PayloadAction<string>) => {
      state.exploreName = action.payload
    },
    setModelName: (state, action: PayloadAction<string>) => {
      state.modelName = action.payload
    },
    setExploreGenerationExamples(
      state,
      action: PayloadAction<
        AssistantState['examples']['exploreGenerationExamples']
      >,
    ) {
      state.examples.exploreGenerationExamples = action.payload
    },
    setExploreRefinementExamples(
      state,
      action: PayloadAction<
        AssistantState['examples']['exploreRefinementExamples']
      >,
    ) {
      state.examples.exploreRefinementExamples = action.payload
    },
    updateSummaryMessage: (
      state,
      action: PayloadAction<{ uuid: string; summary: string }>,
    ) => {
      const { uuid, summary } = action.payload
      if (state.currentExploreThread === null) {
        state.currentExploreThread = newThreadState()
      }
      const message = state.currentExploreThread.messages.find(
        (message) => message.uuid === uuid,
      ) as SummarizeMesage
      message.summary = summary
    },
  },
})

export const {
  setIsQuerying,
  setIsChatMode,
  resetChatMode,
  addToHistory,
  clearHistory,
  updateLastHistoryEntry,
  addPrompt,
  setDimensions,
  setMeasures,
  setExploreUrl,
  setQuery,
  resetChat,
  addMessage,
  setExploreId,
  setExploreName,
  setModelName,
  setExploreGenerationExamples,
  setExploreRefinementExamples,

  updateCurrentThread,
  setCurrentThread,

  openSidePanel,
  closeSidePanel,
  setSidePanelExploreUrl,

  setSetting,
  resetSettings,

  updateSummaryMessage,
} = assistantSlice.actions

export default assistantSlice.reducer
