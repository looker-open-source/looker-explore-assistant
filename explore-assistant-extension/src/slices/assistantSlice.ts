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

interface AssistantState {
  isQuerying: boolean
  history: HistoryItem[]
  dimensions: Field[]
  measures: Field[]
  exploreUrl: string
  query: string
}

const initialState: AssistantState = {
  isQuerying: false,
  history: [],
  dimensions: [],
  measures: [],
  exploreUrl: '',
  query: '',
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
  },
})

export const { setIsQuerying, addToHistory, setHistory, setDimensions, setMeasures, setExploreUrl, setQuery } = assistantSlice.actions

export default assistantSlice.reducer
