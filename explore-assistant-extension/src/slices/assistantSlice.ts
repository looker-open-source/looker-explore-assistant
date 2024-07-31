import { createSlice, PayloadAction } from '@reduxjs/toolkit'

interface HistoryItem {
  message: string
  url: string
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

interface AssistantState {
  isQuerying: boolean
  isChatMode: boolean
  currentExploreThread: ExploreThread
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
}

const initialState: AssistantState = {
  isQuerying: false,
  isChatMode: false,
  currentExploreThread: {
    messages: [],
    exploreUrl: '',
    summarizedPrompt: '',
    promptList: [],
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
  }
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
    addToHistory: (state, action: PayloadAction<HistoryItem>) => {
      state.history.push(action.payload)
    },
    setHistory: (state, action: PayloadAction<HistoryItem[]>) => {
      state.history = action.payload
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
    setExploreGenerationExamples(state, action: PayloadAction<AssistantState['examples']['exploreGeneration']>) {
      state.examples.exploreGenerationExamples = action.payload
    },
    setExploreRefinementExamples(state, action: PayloadAction<AssistantState['examples']['exploreRefinement']>) {
      state.examples.exploreRefinementExamples = action.payload
    },
  },
})

export const {
  setIsQuerying,
  setIsChatMode,
  resetChatMode,
  addToHistory,
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
} = assistantSlice.actions

export default assistantSlice.reducer
