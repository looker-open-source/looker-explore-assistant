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

export interface TrustedDashboards {
  [exploreKey: string]: string // the string is a lookml dashboard text
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
    trustedDashboards: TrustedDashboards
  },
  settings: Settings,
  isBigQueryMetadataLoaded: boolean,
  isSemanticModelLoaded: boolean
}

export const newThreadState = () => {
  const thread: ExploreThread = {    
    uuid: uuidv4(),
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
}

export const initialState: AssistantState = {
  isQuerying: false,
  isChatMode: false,
  currentExploreThread: null,
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
    exploreSamples: {},
    trustedDashboards: {},
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
        state.currentExploreThread = newThreadState()
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
    setTrustedDashboardExamples(
      state,
      action: PayloadAction<AssistantState['examples']['trustedDashboards']>,
    ) {
      state.examples.trustedDashboards = action.payload
    },
  },
})

export const {
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
  addMessage,
  setExploreGenerationExamples,
  setExploreRefinementExamples,
  setExploreSamples,
  setTrustedDashboardExamples,
  
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
