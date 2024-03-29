import { configureStore } from '@reduxjs/toolkit'
import assistantReducer from './slices/assistantSlice'

export const store = configureStore({
  reducer: {
    assistant: assistantReducer,
  },
})

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
