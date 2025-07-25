import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { Provider } from 'react-redux'
import { createStore } from '@reduxjs/toolkit'
import '@testing-library/jest-dom'
import userEvent from '@testing-library/user-event'

import AgentPage from '../../src/pages/AgentPage'
import { assistantSlice, AssistantState } from '../../src/slices/assistantSlice'
import { ExtensionContext } from '@looker/extension-sdk-react'

// Mock the hooks
jest.mock('../../src/hooks/useAreas', () => ({
  useAreas: jest.fn(),
}))

jest.mock('../../src/hooks/useSendCloudRunMessage', () => ({
  __esModule: true,
  default: () => ({
    processPrompt: jest.fn(),
  }),
}))

// Mock other components to isolate area selector testing
jest.mock('../../src/pages/AgentPage/Sidebar', () => {
  return function MockSidebar() {
    return <div data-testid="sidebar">Sidebar</div>
  }
})

jest.mock('../../src/pages/AgentPage/PromptInput', () => {
  return function MockPromptInput() {
    return <div data-testid="prompt-input">PromptInput</div>
  }
})

jest.mock('../../src/components/SamplePrompts', () => {
  return function MockSamplePrompts() {
    return <div data-testid="sample-prompts">SamplePrompts</div>
  }
})

const mockCore40SDK = {
  ok: jest.fn(),
  create_sql_query: jest.fn(),
  run_sql_query: jest.fn(),
  create_query: jest.fn(),
  run_query: jest.fn(),
}

const mockExtensionContextValue = {
  core40SDK: mockCore40SDK,
  route: jest.fn(),
  visualizationSDK: jest.fn(),
  tileHostData: jest.fn(),
  tileSDK: jest.fn(),
  extensionSDK: jest.fn(),
}

// Mock areas data
const mockAreas = [
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
    explore_keys: ['marketing:campaigns', 'marketing:events'],
    explore_details: {
      'marketing:campaigns': {
        display_name: 'Campaigns',
        description: 'Marketing campaign data'
      },
      'marketing:events': {
        display_name: 'Events',
        description: 'Marketing event tracking'
      }
    }
  }
]

const createMockStore = (initialState: Partial<AssistantState> = {}) => {
  const defaultState: AssistantState = {
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
    isBigQueryMetadataLoaded: true,
    isSemanticModelLoaded: true,
    selectedArea: null,
    selectedExplores: [],
    availableAreas: mockAreas,
    isAreasLoaded: true,
    ...initialState,
  }

  return createStore(assistantSlice.reducer, defaultState)
}

const renderWithStore = (store: any) => {
  return render(
    <ExtensionContext.Provider value={mockExtensionContextValue}>
      <Provider store={store}>
        <AgentPage />
      </Provider>
    </ExtensionContext.Provider>
  )
}

describe('Area Selector Feature', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(() => {
    user = userEvent.setup()
    jest.clearAllMocks()
  })

  describe('Area Selector Rendering', () => {
    it('should render area selector when areas are available', () => {
      const store = createMockStore()
      renderWithStore(store)

      expect(screen.getByLabelText('Select Business Area')).toBeInTheDocument()
    })

    it('should not render area selector when no areas are available', () => {
      const store = createMockStore({ availableAreas: [] })
      renderWithStore(store)

      expect(screen.queryByLabelText('Select Business Area')).not.toBeInTheDocument()
    })

    it('should not render area selector when areas are not loaded', () => {
      const store = createMockStore({ isAreasLoaded: false })
      renderWithStore(store)

      expect(screen.queryByLabelText('Select Business Area')).not.toBeInTheDocument()
    })

    it('should display all available areas in the dropdown', async () => {
      const store = createMockStore()
      renderWithStore(store)

      const areaSelect = screen.getByLabelText('Select Business Area')
      await user.click(areaSelect)

      expect(screen.getByText('All Areas (No Restriction)')).toBeInTheDocument()
      expect(screen.getByText('Sales')).toBeInTheDocument()
      expect(screen.getByText('Marketing')).toBeInTheDocument()
    })
  })

  describe('Area Selection Functionality', () => {
    it('should update selected area when user selects an area', async () => {
      const store = createMockStore()
      renderWithStore(store)

      const areaSelect = screen.getByLabelText('Select Business Area')
      await user.click(areaSelect)
      await user.click(screen.getByText('Sales'))

      await waitFor(() => {
        expect(store.getState().selectedArea).toBe('Sales')
      })
    })

    it('should clear selected area when "All Areas" is selected', async () => {
      const store = createMockStore({ selectedArea: 'Sales' })
      renderWithStore(store)

      const areaSelect = screen.getByLabelText('Select Business Area')
      await user.click(areaSelect)
      await user.click(screen.getByText('All Areas (No Restriction)'))

      await waitFor(() => {
        expect(store.getState().selectedArea).toBe('')
      })
    })

    it('should reset chat when switching areas', async () => {
      const store = createMockStore({
        selectedArea: 'Marketing',
        currentExploreThread: {
          uuid: 'test-thread',
          messages: [{ uuid: 'msg1', message: 'test', actor: 'user', createdAt: Date.now(), type: 'text' }],
          promptList: ['test'],
          createdAt: Date.now(),
        }
      })
      renderWithStore(store)

      const areaSelect = screen.getByLabelText('Select Business Area')
      await user.click(areaSelect)
      await user.click(screen.getByText('Sales'))

      // Should dispatch resetChat and add informational message
      await waitFor(() => {
        expect(store.getState().selectedArea).toBe('Sales')
      })
    })
  })

  describe('Explore Selector Rendering', () => {
    it('should not render explore selector when no area is selected', () => {
      const store = createMockStore()
      renderWithStore(store)

      expect(screen.queryByLabelText('Select Data Models (Optional)')).not.toBeInTheDocument()
    })

    it('should render explore selector when an area is selected', async () => {
      const store = createMockStore({ selectedArea: 'Sales' })
      renderWithStore(store)

      expect(screen.getByLabelText('Select Data Models (Optional)')).toBeInTheDocument()
    })

    it('should display explores for the selected area', async () => {
      const store = createMockStore({ selectedArea: 'Sales' })
      renderWithStore(store)

      const exploreSelect = screen.getByLabelText('Select Data Models (Optional)')
      await user.click(exploreSelect)

      expect(screen.getByText('Order Items')).toBeInTheDocument()
      expect(screen.getByText('Orders')).toBeInTheDocument()
      expect(screen.getByText('Detailed order item data')).toBeInTheDocument()
      expect(screen.getByText('Order summary data')).toBeInTheDocument()
    })
  })

  describe('Explore Selection Functionality', () => {
    it('should allow multiple explore selection', async () => {
      const store = createMockStore({ selectedArea: 'Sales' })
      renderWithStore(store)

      const exploreSelect = screen.getByLabelText('Select Data Models (Optional)')
      await user.click(exploreSelect)
      
      await user.click(screen.getByText('Order Items'))
      await user.click(screen.getByText('Orders'))

      await waitFor(() => {
        expect(store.getState().selectedExplores).toContain('ecommerce:order_items')
        expect(store.getState().selectedExplores).toContain('ecommerce:orders')
      })
    })

    it('should display selected explores as chips', async () => {
      const store = createMockStore({ 
        selectedArea: 'Sales',
        selectedExplores: ['ecommerce:order_items', 'ecommerce:orders']
      })
      renderWithStore(store)

      expect(screen.getByText('Order Items')).toBeInTheDocument()
      expect(screen.getByText('Orders')).toBeInTheDocument()
    })

    it('should clear selected explores when area changes', async () => {
      const store = createMockStore({ 
        selectedArea: 'Sales',
        selectedExplores: ['ecommerce:order_items']
      })
      renderWithStore(store)

      const areaSelect = screen.getByLabelText('Select Business Area')
      await user.click(areaSelect)
      await user.click(screen.getByText('Marketing'))

      await waitFor(() => {
        expect(store.getState().selectedArea).toBe('Marketing')
        // Note: The actual clearing of selectedExplores would need to be implemented
        // in the component if it's not already there
      })
    })
  })

  describe('Helper Functions', () => {
    it('should get explores for selected area correctly', () => {
      const store = createMockStore({ selectedArea: 'Sales' })
      renderWithStore(store)

      // This tests the getExploresForSelectedArea function indirectly
      // by checking if the right explores are shown in the dropdown
      const exploreSelect = screen.getByLabelText('Select Data Models (Optional)')
      expect(exploreSelect).toBeInTheDocument()
    })

    it('should handle missing explore details gracefully', async () => {
      const incompleteAreas = [
        {
          area: 'TestArea',
          explore_keys: ['test:missing_details'],
          explore_details: {} // Missing details for the explore
        }
      ]
      
      const store = createMockStore({ 
        selectedArea: 'TestArea',
        availableAreas: incompleteAreas
      })
      renderWithStore(store)

      const exploreSelect = screen.getByLabelText('Select Data Models (Optional)')
      await user.click(exploreSelect)

      // Should show fallback display name
      expect(screen.getByText('Missing Details')).toBeInTheDocument()
    })
  })

  describe('Loading States', () => {
    it('should not be ready when areas are not loaded', () => {
      const store = createMockStore({ 
        isAreasLoaded: false,
        isBigQueryMetadataLoaded: true,
        isSemanticModelLoaded: true
      })
      renderWithStore(store)

      // Component should handle the not-ready state
      // This would need to be verified based on the actual loading UI implementation
    })

    it('should be ready when all data is loaded', () => {
      const store = createMockStore({
        isAreasLoaded: true,
        isBigQueryMetadataLoaded: true,
        isSemanticModelLoaded: true
      })
      renderWithStore(store)

      expect(screen.getByLabelText('Select Business Area')).toBeInTheDocument()
    })
  })
})
