import { configureStore } from '@reduxjs/toolkit'
import { persistStore, persistReducer, createTransform } from 'redux-persist'
import storage from 'redux-persist/lib/storage' // defaults to localStorage for web
import { combineReducers } from 'redux'
import assistantReducer, {
  AssistantState,
  initialState,
  Settings,
} from './slices/assistantSlice'

// Define keys that should never be persisted
const neverPersistKeys: (keyof AssistantState)[] = [
  'dimensions',
  'measures',
  'examples',
]

// Create a transform function to filter out specific keys
const filterTransform = createTransform(
  // transform state on its way to being serialized and persisted.
  (inboundState: unknown, key) => {
    if (key === 'assistant') {
      const assistantState = inboundState as AssistantState
      const newState = { ...assistantState }
      neverPersistKeys.forEach((key) => {
        delete newState[key]
      })

      // Only keep settings that exist in the initial state
      const persistedSettings: Partial<Settings> = {}
      Object.keys(newState.settings).forEach((settingKey) => {
        if (settingKey in initialState.settings) {
          persistedSettings[settingKey] = newState.settings[settingKey]
        }
      })

      return newState
    }
    return inboundState
  },
  // transform state being rehydrated
  (outboundState: unknown, key) => {
    if (key === 'assistant') {
      const persistedState = outboundState as Partial<AssistantState>
      const mergedState = { ...initialState, ...persistedState }

      // Ensure all settings from initial state are present
      mergedState.settings = {
        ...initialState.settings,
        ...mergedState.settings,
      }

      return mergedState
    }
    return outboundState
  },
)

const persistConfig = {
  key: 'root',
  storage,
  whitelist: ['assistant'], // only assistant will be persisted
  transforms: [filterTransform],
}

const rootReducer = combineReducers({
  assistant: assistantReducer,
})

const persistedReducer = persistReducer(persistConfig, rootReducer)

export const store = configureStore({
  reducer: persistedReducer,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: ['persist/PERSIST'],
      },
    }),
})

export const persistor = persistStore(store)

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
