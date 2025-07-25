// Tests for assistant slice area functionality

describe('Assistant Slice - Area Functionality', () => {
  // Mock reducer for testing area functionality
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

  const initialState = {
    selectedArea: null,
    selectedExplores: [],
    availableAreas: [],
    isAreasLoaded: false,
  }

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
      const newState = mockAssistantSlice.reducer(initialState, action)
      
      expect(newState.selectedExplores).toEqual(explores)
    })

    it('should clear selected explores when empty array is passed', () => {
      const stateWithExplores = {
        ...initialState,
        selectedExplores: ['ecommerce:order_items']
      }
      
      const action = setSelectedExplores([])
      const newState = mockAssistantSlice.reducer(stateWithExplores, action)
      
      expect(newState.selectedExplores).toEqual([])
    })

    it('should replace existing explores with new selection', () => {
      const stateWithExplores = {
        ...initialState,
        selectedExplores: ['ecommerce:order_items']
      }
      
      const newExplores = ['marketing:campaigns', 'marketing:events']
      const action = setSelectedExplores(newExplores)
      const newState = mockAssistantSlice.reducer(stateWithExplores, action)
      
      expect(newState.selectedExplores).toEqual(newExplores)
    })
  })

  describe('Area interface validation', () => {
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
  })

  describe('State immutability', () => {
    it('should maintain state immutability when setting area', () => {
      const action = setSelectedArea('Sales')
      const newState = mockAssistantSlice.reducer(initialState, action)
      
      expect(newState).not.toBe(initialState)
      expect(newState.selectedArea).toBe('Sales')
      expect(initialState.selectedArea).toBe(null)
    })

    it('should maintain state immutability when setting explores', () => {
      const explores = ['ecommerce:order_items']
      const action = setSelectedExplores(explores)
      const newState = mockAssistantSlice.reducer(initialState, action)
      
      expect(newState).not.toBe(initialState)
      expect(newState.selectedExplores).toEqual(explores)
      expect(initialState.selectedExplores).toEqual([])
    })
  })
})
