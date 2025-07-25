// Tests for SamplePrompts component with area selector integration

import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import { Provider } from 'react-redux'
import { configureStore } from '@reduxjs/toolkit'
import '@testing-library/jest-dom'

import SamplePrompts from '../../src/components/SamplePrompts'
import { assistantSlice, AssistantState } from '../../src/slices/assistantSlice'

// Mock the dispatch actions
const mockDispatch = jest.fn()
jest.mock('react-redux', () => ({
  ...jest.requireActual('react-redux'),
  useDispatch: () => mockDispatch,
}))

const createMockStore = (initialState: Partial<AssistantState> = {}) => {
  const defaultState: AssistantState = {
    isChatMode: false,
    query: '',
    isQuerying: false,
    currentExploreThread: null,
    currentExplore: {
      modelName: 'ecommerce',
      exploreId: 'order_items',
      exploreKey: 'ecommerce:order_items',
    },
    sidePanel: {
      isSidePanelOpen: false,
      exploreParams: {},
    },
    examples: {
      exploreSamples: {
        'ecommerce:order_items': [
          {
            prompt: 'Show me total sales by month',
            category: 'Sales Analysis'
          },
          {
            prompt: 'What are the top selling products?',
            category: 'Product Analysis'
          }
        ],
        'ecommerce:orders': [
          {
            prompt: 'How many orders were placed last week?',
            category: 'Order Metrics'
          }
        ],
        'marketing:campaigns': [
          {
            prompt: 'Show campaign performance by channel',
            category: 'Campaign Analysis'
          }
        ]
      },
      exploreGenerationExamples: {},
      exploreRefinementExamples: {},
      exploreEntries: {},
    },
    semanticModels: {},
    isBigQueryMetadataLoaded: true,
    isSemanticModelLoaded: true,
    selectedArea: null,
    selectedExplores: [],
    availableAreas: [
      {
        area: 'Sales',
        explore_keys: ['ecommerce:order_items', 'ecommerce:orders'],
        explore_details: {
          'ecommerce:order_items': {
            display_name: 'Order Items',
            description: 'Detailed order item data'
          },
          'ecommerce:orders': {
            display_name: 'Orders',
            description: 'Order summary data'
          }
        }
      },
      {
        area: 'Marketing',
        explore_keys: ['marketing:campaigns'],
        explore_details: {
          'marketing:campaigns': {
            display_name: 'Campaigns',
            description: 'Marketing campaign data'
          }
        }
      }
    ],
    isAreasLoaded: true,
    history: [],
    settings: {} as any,
    testsSuccessful: true,
    bigQueryTestSuccessful: true,
    vertexTestSuccessful: true,
    oauth: {
      token: null,
      isAuthenticating: false,
      hasValidToken: false,
    },
    modelDetails: {},
    ...initialState,
  }

  return configureStore({
    reducer: {
      assistant: assistantSlice.reducer
    },
    preloadedState: {
      assistant: defaultState
    }
  })
}

const renderWithStore = (store: any) => {
  return render(
    <Provider store={store}>
      <SamplePrompts />
    </Provider>
  )
}

describe('SamplePrompts with Area Selector', () => {
  beforeEach(() => {
    mockDispatch.mockClear()
  })

  describe('Area and Explore Selection Requirements', () => {
    it('should show message when no area is selected', () => {
      const store = createMockStore({
        selectedArea: null,
        selectedExplores: []
      })
      renderWithStore(store)

      expect(screen.getByText('Please select a business area and one or more data models to see sample prompts')).toBeInTheDocument()
    })

    it('should show message when area is selected but no explores', () => {
      const store = createMockStore({
        selectedArea: 'Sales',
        selectedExplores: []
      })
      renderWithStore(store)

      expect(screen.getByText('Please select a business area and one or more data models to see sample prompts')).toBeInTheDocument()
    })

    it('should show message when explores are selected but no area', () => {
      const store = createMockStore({
        selectedArea: null,
        selectedExplores: ['ecommerce:order_items']
      })
      renderWithStore(store)

      expect(screen.getByText('Please select a business area and one or more data models to see sample prompts')).toBeInTheDocument()
    })
  })

  describe('Sample Prompts Display', () => {
    it('should show sample prompts when area and explores are selected', () => {
      const store = createMockStore({
        selectedArea: 'Sales',
        selectedExplores: ['ecommerce:order_items']
      })
      renderWithStore(store)

      expect(screen.getByText('Sample prompts for Sales area')).toBeInTheDocument()
      expect(screen.getByText('Show me total sales by month')).toBeInTheDocument()
      expect(screen.getByText('What are the top selling products?')).toBeInTheDocument()
    })

    it('should show prompts from multiple selected explores', () => {
      const store = createMockStore({
        selectedArea: 'Sales',
        selectedExplores: ['ecommerce:order_items', 'ecommerce:orders']
      })
      renderWithStore(store)

      expect(screen.getByText('Sample prompts for Sales area (2 data models selected)')).toBeInTheDocument()
      expect(screen.getByText('Show me total sales by month')).toBeInTheDocument()
      expect(screen.getByText('How many orders were placed last week?')).toBeInTheDocument()
    })

    it('should include explore context in categories', () => {
      const store = createMockStore({
        selectedArea: 'Sales',
        selectedExplores: ['ecommerce:order_items', 'ecommerce:orders']
      })
      renderWithStore(store)

      expect(screen.getByText('Sales Analysis (Order Items)')).toBeInTheDocument()
      expect(screen.getByText('Order Metrics (Orders)')).toBeInTheDocument()
    })

    it('should show no prompts message when selected explores have no samples', () => {
      const store = createMockStore({
        selectedArea: 'Sales',
        selectedExplores: ['nonexistent:explore'],
        examples: {
          exploreSamples: {},
          exploreGenerationExamples: {},
          exploreRefinementExamples: {},
          exploreEntries: {},
        }
      })
      renderWithStore(store)

      expect(screen.getByText('No sample prompts available for the selected data models')).toBeInTheDocument()
    })
  })

  describe('Sample Prompt Interaction', () => {
    it('should dispatch actions when a sample prompt is clicked', () => {
      const store = createMockStore({
        selectedArea: 'Sales',
        selectedExplores: ['ecommerce:order_items']
      })
      renderWithStore(store)

      const promptElement = screen.getByText('Show me total sales by month')
      fireEvent.click(promptElement)

      expect(mockDispatch).toHaveBeenCalledWith({
        type: 'assistant/setQuery',
        payload: 'Show me total sales by month'
      })
      expect(mockDispatch).toHaveBeenCalledWith({
        type: 'assistant/setIsChatMode',
        payload: true
      })
    })
  })

  describe('Explore Display Name Logic', () => {
    it('should use display names from area details when available', () => {
      const store = createMockStore({
        selectedArea: 'Sales',
        selectedExplores: ['ecommerce:order_items']
      })
      renderWithStore(store)

      expect(screen.getByText('Sales Analysis (Order Items)')).toBeInTheDocument()
    })

    it('should create fallback display names when area details are missing', () => {
      const store = createMockStore({
        selectedArea: 'Sales',
        selectedExplores: ['test:some_explore'],
        availableAreas: [
          {
            area: 'Sales',
            explore_keys: ['test:some_explore'],
            explore_details: {} // Missing details
          }
        ],
        examples: {
          exploreSamples: {
            'test:some_explore': [
              {
                prompt: 'Test prompt',
                category: 'Test'
              }
            ]
          },
          exploreGenerationExamples: {},
          exploreRefinementExamples: {},
          exploreEntries: {},
        }
      })
      renderWithStore(store)

      expect(screen.getByText('Test (Some Explore)')).toBeInTheDocument()
    })
  })

  describe('Edge Cases', () => {
    it('should handle string-based sample prompts', () => {
      const store = createMockStore({
        selectedArea: 'Sales',
        selectedExplores: ['ecommerce:string_samples'],
        examples: {
          exploreSamples: {
            'ecommerce:string_samples': [
              'Simple string prompt',
              'Another string prompt'
            ]
          },
          exploreGenerationExamples: {},
          exploreRefinementExamples: {},
          exploreEntries: {},
        }
      })
      renderWithStore(store)

      expect(screen.getByText('Simple string prompt')).toBeInTheDocument()
      expect(screen.getByText('Another string prompt')).toBeInTheDocument()
    })

    it('should filter out invalid sample prompts', () => {
      const store = createMockStore({
        selectedArea: 'Sales',
        selectedExplores: ['ecommerce:mixed_samples'],
        examples: {
          exploreSamples: {
            'ecommerce:mixed_samples': [
              'Valid prompt',
              '', // Empty string
              null, // Null value
              { prompt: 'Valid object prompt', category: 'Test' },
              { prompt: '', category: 'Invalid' }, // Empty prompt
            ]
          },
          exploreGenerationExamples: {},
          exploreRefinementExamples: {},
          exploreEntries: {},
        }
      })
      renderWithStore(store)

      expect(screen.getByText('Valid prompt')).toBeInTheDocument()
      expect(screen.getByText('Valid object prompt')).toBeInTheDocument()
      expect(screen.queryByText('')).not.toBeInTheDocument()
    })
  })
})
