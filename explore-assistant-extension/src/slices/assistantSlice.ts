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
  intent: 'exploreRefinement' | 'summarize' | 'dataQuestion'
}

interface ExploreMessage {
  exploreUrl: string
  actor: 'system'
  createdAt: number
  type: 'explore'
  summarizedPrompt: string
}

interface SummarizeMessage {
  exploreUrl: string
  actor: 'system'
  createdAt: number
  type: 'summarize'
}

type ChatMessage = Message | ExploreMessage | SummarizeMessage

interface Sample {
  category: string
  prompt: string
  color: string
}

export interface ExploreMetadata {
  description: string
  label: string
}

interface AssistantState {
  isQuerying: boolean
  history: HistoryItem[]
  dimensions: Field[]
  measures: Field[]
  exploreUrl: string
  query: string
  messageThread: ChatMessage[]
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
  exploreExamplesById: {
    [exploreId: string]: {
      input: string
      output: string
    }[]
  }
  exploreSamplesById: {
    [exploreId: string]: Sample[]
  }
  exploreMetadataById: {
    [exploreId: string]: ExploreMetadata
  }
  exploreDimensionsById: {
    [exploreId: string]: Field[]
  }
  exploreMeasuresById: {
    [exploreId: string]: Field[]
  }
}

const initialState: AssistantState = {
  isQuerying: false,
  history: [],
  dimensions: [],
  measures: [],
  exploreUrl: '',
  query: '',
  messageThread: [],
  exploreId: '',
  exploreName: '',
  modelName: '',
  examples: {
    exploreGenerationExamples: [],
    exploreRefinementExamples: [],
  },
  exploreExamplesById: {},
  exploreSamplesById: {},
  exploreMetadataById: {},
  exploreDimensionsById: {},
  exploreMeasuresById: {},
}

export const assistantSlice = createSlice({
  name: 'assistant',
  initialState,
  reducers: {
    setIsQuerying: (state, action: PayloadAction<boolean>) => {
      state.isQuerying = action.payload
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
      state.exploreUrl = action.payload
    },
    setQuery: (state, action: PayloadAction<string>) => {
      state.query = action.payload
    },
    resetChat: (state) => {
      state.messageThread = []
      state.query = ''
      state.exploreUrl = ''
    },
    addMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.messageThread.push(action.payload)
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
    setExploreExamplesById: (
      state,
      action: PayloadAction<{
        [exploreId: string]: { input: string; output: string }[]
      }>,
    ) => {
      const examplesById = action.payload
      for (const [exploreId, examples] of Object.entries(examplesById)) {
        state.exploreExamplesById[exploreId] = examples
      }
    },
    setExploreSamplesById: (
      state,
      action: PayloadAction<{ [exploreId: string]: Sample[] }>,
    ) => {
      const samplesById = action.payload
      for (const [exploreId, samples] of Object.entries(samplesById)) {
        state.exploreSamplesById[exploreId] = samples
      }
    },
    setExploreMetadataById: (
      state,
      action: PayloadAction<{ [exploreId: string]: ExploreMetadata }>,
    ) => {
      const metadataById = action.payload
      for (const [exploreId, metadata] of Object.entries(metadataById)) {
        state.exploreMetadataById[exploreId] = metadata
      }
    },
    setExploreDimensionsById: (
      state,
      action: PayloadAction<{ [exploreId: string]: Field[] }>,
    ) => {
      const dimensionsById = action.payload
      for (const [exploreId, fields] of Object.entries(dimensionsById)) {
        state.exploreDimensionsById[exploreId] = fields
      }
    },
    setExploreMeasuresById: (
      state,
      action: PayloadAction<{ [exploreId: string]: Field[] }>,
    ) => {
      const measuresById = action.payload
      for (const [exploreId, fields] of Object.entries(measuresById)) {
        state.exploreMeasuresById[exploreId] = fields
      }
    },
  },
})

export const {
  setIsQuerying,
  addToHistory,
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
  setExploreExamplesById,
  setExploreSamplesById,
  setExploreMetadataById,
  setExploreDimensionsById,
  setExploreMeasuresById,
} = assistantSlice.actions

export default assistantSlice.reducer
