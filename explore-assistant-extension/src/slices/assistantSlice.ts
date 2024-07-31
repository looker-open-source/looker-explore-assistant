import { createSlice, PayloadAction } from '@reduxjs/toolkit'

export interface Setting {
  name: string
  description: string
  value: boolean
}

export interface Settings {
  [key: string]: Setting
}

interface HistoryItem {
  message: string
  createdAt: number
}

interface Field {
  name: string
  type: string
  description: string
  tags: string[]
}

interface Message {
  message: string
  actor: 'user' | 'system'
  createdAt: number
  type: 'text'
  intent?: 'exploreRefinement' | 'summarize' | 'dataQuestion'
}

interface ExploreMessage {
  exploreUrl: string
  actor: 'system'
  createdAt: number
  type: 'explore'
  summarizedPrompt: string
}

interface SummarizeMesage {
  exploreUrl: string
  actor: 'system'
  createdAt: number
  type: 'summarize'
}

type ChatMessage = Message | ExploreMessage | SummarizeMesage

type ExploreThread = {
  messages: ChatMessage[]
  exploreUrl: string
  summarizedPrompt: string
  promptList: string[]
}

export interface AssistantState {
  isQuerying: boolean
  isChatMode: boolean
  currentExploreThread: ExploreThread
  sidePanel: {
    isSidePanelOpen: boolean
    exploreUrl: string
  }
  history: HistoryItem[]
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

export const initialState: AssistantState = {
  isQuerying: false,
  isChatMode: false,
  currentExploreThread: {
    messages: [],
    exploreUrl: '',
    summarizedPrompt: '',
    promptList: [],
  },
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
      resetChat()
    },
    resetSettings: (state) => {
      state.settings = initialState.settings
    },
    setSetting: (
      state,
      action: PayloadAction<{ id: keyof Settings; value: boolean }>
    ) => {
      const { id, value } = action.payload;
      if (state.settings[id]) {
        state.settings[id].value = value;
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
    updateLastHistoryEntry: (state, action: PayloadAction<string>) => {
      state.history[state.history.length - 1] = {
        message: action.payload,
        createdAt: Date.now(),
      }
    },
    addToHistory: (state, action: PayloadAction<string>) => {
      state.history.push({
        message: action.payload,
        createdAt: Date.now(),
      })
    },
    setHistory: (state, action: PayloadAction<HistoryItem[]>) => {
      state.history = action.payload
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
      state.currentExploreThread.exploreUrl = action.payload
    },
    setQuery: (state, action: PayloadAction<string>) => {
      state.query = action.payload
    },
    resetChat: (state) => {
      state.currentExploreThread = initialState.currentExploreThread
      state.query = ''
      state.isChatMode = false
      state.isQuerying = false
      state.sidePanel = initialState.sidePanel
    },
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.currentExploreThread.messages.push(action.payload)
    },
    addPrompt: (state, action: PayloadAction<string>) => {
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
      action: PayloadAction<AssistantState['examples']['exploreGeneration']>,
    ) {
      state.examples.exploreGenerationExamples = action.payload
    },
    setExploreRefinementExamples(
      state,
      action: PayloadAction<AssistantState['examples']['exploreRefinement']>,
    ) {
      state.examples.exploreRefinementExamples = action.payload
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
  setHistory,
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

  openSidePanel,
  closeSidePanel,
  setSidePanelExploreUrl,

  setSetting,
  resetSettings,
} = assistantSlice.actions

export default assistantSlice.reducer
