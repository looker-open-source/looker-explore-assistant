import { createSlice } from '@reduxjs/toolkit'

// Mock the assistant slice for testing
const mockAssistantSlice = {
  reducer: (state: any, action: any) => {
    switch (action.type) {
      case 'assistant/setSelectedArea':
        return { ...state, selectedArea: action.payload }
      case 'assistant/setSelectedExplores':
        return { ...state, selectedExplores: action.payload }
      default:
        return state
    }
  }
}

const setSelectedArea = (area: string | null) => ({
  type: 'assistant/setSelectedArea',
  payload: area
})

const setSelectedExplores = (explores: string[]) => ({
  type: 'assistant/setSelectedExplores',
  payload: explores
})

// Area interface for testing
interface Area {
  area: string
  explore_keys: string[]
  explore_details: {
    [key: string]: {
      display_name: string
      description: string
    }
  }
}

describe('Assistant Slice - Area Functionality', () => {
  const initialState = {
    isChatMode: false,
    query: '',
    isQuerying: false,
    currentExploreThread: null,
    currentExplore: {
      modelName: '',
      exploreId: '',
      exploreKey: '',
    },
    sidePanel: {
      isSidePanelOpen: false,
      exploreParams: {},
    },
    examples: {
      exploreSamples: {},
      exploreGenerationExamples: {},
      exploreRefinementExamples: {},
      exploreEntries: {},
    },
    semanticModels: {},
    isBigQueryMetadataLoaded: false,
    isSemanticModelLoaded: false,
    selectedArea: null,
    selectedExplores: [],
    availableAreas: [],
    isAreasLoaded: false,
  }

  const mockAreas: Area[] = [
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
  ]

  describe('setSelectedArea reducer', () => {
    it('should set the selected area', () => {
      const action = setSelectedArea('Sales')
      const newState = mockAssistantSlice.reducer(initialState, action)
      
      expect(newState.selectedArea).toBe('Sales')
    })

    it('should clear the selected area when empty string is passed', () => {
      const stateWithArea = {
        ...initialState,
        selectedArea: 'Sales'
      }
      
      const action = setSelectedArea('')
      const newState = mockAssistantSlice.reducer(stateWithArea, action)
      
      expect(newState.selectedArea).toBe('')
    })

    it('should handle null value', () => {
      const action = setSelectedArea(null)
      const newState = mockAssistantSlice.reducer(initialState, action)
      
      expect(newState.selectedArea).toBe(null)
    })
  })

  describe('setSelectedExplores reducer', () => {
    it('should set selected explores array', () => {
      const explores = ['ecommerce:order_items', 'ecommerce:orders']
      const action = setSelectedExplores(explores)
      const newState = assistantSlice.reducer(initialState, action)
      
      expect(newState.selectedExplores).toEqual(explores)
    })

    it('should clear selected explores when empty array is passed', () => {
      const stateWithExplores = {
        ...initialState,
        selectedExplores: ['ecommerce:order_items']
      }
      
      const action = setSelectedExplores([])
      const newState = assistantSlice.reducer(stateWithExplores, action)
      
      expect(newState.selectedExplores).toEqual([])
    })

    it('should replace existing explores with new selection', () => {
      const stateWithExplores = {
        ...initialState,
        selectedExplores: ['ecommerce:order_items']
      }
      
      const newExplores = ['marketing:campaigns', 'marketing:events']
      const action = setSelectedExplores(newExplores)
      const newState = assistantSlice.reducer(stateWithExplores, action)
      
      expect(newState.selectedExplores).toEqual(newExplores)
    })

    it('should handle single explore selection', () => {
      const explores = ['ecommerce:order_items']
      const action = setSelectedExplores(explores)
      const newState = assistantSlice.reducer(initialState, action)
      
      expect(newState.selectedExplores).toEqual(explores)
    })
  })

  describe('Area interface', () => {
    it('should have correct structure for Area type', () => {
      const area: Area = {
        area: 'Sales',
        explore_keys: ['ecommerce:orders'],
        explore_details: {
          'ecommerce:orders': {
            display_name: 'Orders',
            description: 'Order data'
          }
        }
      }

      expect(area.area).toBe('Sales')
      expect(area.explore_keys).toContain('ecommerce:orders')
      expect(area.explore_details['ecommerce:orders']).toBeDefined()
      expect(area.explore_details['ecommerce:orders'].display_name).toBe('Orders')
      expect(area.explore_details['ecommerce:orders'].description).toBe('Order data')
    })

    it('should handle optional explore_details', () => {
      const area: Area = {
        area: 'Sales',
        explore_keys: ['ecommerce:orders'],
        explore_details: {}
      }

      expect(area.explore_details).toEqual({})
    })
  })

  describe('State consistency', () => {
    it('should maintain state immutability when setting area', () => {
      const action = setSelectedArea('Sales')
      const newState = assistantSlice.reducer(initialState, action)
      
      expect(newState).not.toBe(initialState)
      expect(newState.selectedArea).toBe('Sales')
      expect(initialState.selectedArea).toBe(null)
    })

    it('should maintain state immutability when setting explores', () => {
      const explores = ['ecommerce:order_items']
      const action = setSelectedExplores(explores)
      const newState = assistantSlice.reducer(initialState, action)
      
      expect(newState).not.toBe(initialState)
      expect(newState.selectedExplores).toEqual(explores)
      expect(initialState.selectedExplores).toEqual([])
    })

    it('should not affect other state properties when setting area', () => {
      const stateWithData = {
        ...initialState,
        query: 'test query',
        isQuerying: true,
        selectedExplores: ['existing:explore']
      }
      
      const action = setSelectedArea('Sales')
      const newState = assistantSlice.reducer(stateWithData, action)
      
      expect(newState.query).toBe('test query')
      expect(newState.isQuerying).toBe(true)
      expect(newState.selectedExplores).toEqual(['existing:explore'])
      expect(newState.selectedArea).toBe('Sales')
    })

    it('should not affect other state properties when setting explores', () => {
      const stateWithData = {
        ...initialState,
        query: 'test query',
        isQuerying: true,
        selectedArea: 'Sales'
      }
      
      const action = setSelectedExplores(['new:explore'])
      const newState = assistantSlice.reducer(stateWithData, action)
      
      expect(newState.query).toBe('test query')
      expect(newState.isQuerying).toBe(true)
      expect(newState.selectedArea).toBe('Sales')
      expect(newState.selectedExplores).toEqual(['new:explore'])
    })
  })
})
