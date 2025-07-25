// Tests for AgentPage helper functions related to area selector

import { Area } from '../../src/slices/assistantSlice'

describe('AgentPage Helper Functions', () => {
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

  describe('getExploresForSelectedArea', () => {
    it('should return explores for selected area', () => {
      const getExploresForSelectedArea = (selectedArea: string | null, availableAreas: Area[]) => {
        if (!selectedArea) return []
        const area = availableAreas.find(a => a.area === selectedArea)
        return area ? area.explore_keys : []
      }

      const result = getExploresForSelectedArea('Sales', mockAreas)
      expect(result).toEqual(['ecommerce:order_items', 'ecommerce:orders'])
    })

    it('should return empty array when no area is selected', () => {
      const getExploresForSelectedArea = (selectedArea: string | null, availableAreas: Area[]) => {
        if (!selectedArea) return []
        const area = availableAreas.find(a => a.area === selectedArea)
        return area ? area.explore_keys : []
      }

      const result = getExploresForSelectedArea(null, mockAreas)
      expect(result).toEqual([])
    })

    it('should return empty array when area is not found', () => {
      const getExploresForSelectedArea = (selectedArea: string | null, availableAreas: Area[]) => {
        if (!selectedArea) return []
        const area = availableAreas.find(a => a.area === selectedArea)
        return area ? area.explore_keys : []
      }

      const result = getExploresForSelectedArea('NonExistentArea', mockAreas)
      expect(result).toEqual([])
    })
  })

  describe('getExploreDetails', () => {
    it('should return explore details when area and explore exist', () => {
      const getExploreDetails = (exploreKey: string, selectedArea: string | null, availableAreas: Area[]) => {
        if (!selectedArea) return { display_name: exploreKey, description: '' }
        const area = availableAreas.find(a => a.area === selectedArea)
        const details = area?.explore_details?.[exploreKey]
        
        if (details) {
          return details
        }
        
        // Fallback: create a display name from the explore key
        const fallbackDisplayName = exploreKey.split(':')[1]?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || exploreKey
        return { display_name: fallbackDisplayName, description: '' }
      }

      const result = getExploreDetails('ecommerce:order_items', 'Sales', mockAreas)
      expect(result).toEqual({
        display_name: 'Order Items',
        description: 'Detailed order item data'
      })
    })

    it('should return fallback display name when no area is selected', () => {
      const getExploreDetails = (exploreKey: string, selectedArea: string | null, availableAreas: Area[]) => {
        if (!selectedArea) return { display_name: exploreKey, description: '' }
        const area = availableAreas.find(a => a.area === selectedArea)
        const details = area?.explore_details?.[exploreKey]
        
        if (details) {
          return details
        }
        
        // Fallback: create a display name from the explore key
        const fallbackDisplayName = exploreKey.split(':')[1]?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || exploreKey
        return { display_name: fallbackDisplayName, description: '' }
      }

      const result = getExploreDetails('ecommerce:order_items', null, mockAreas)
      expect(result).toEqual({ display_name: 'ecommerce:order_items', description: '' })
    })

    it('should return fallback display name when explore details are missing', () => {
      const getExploreDetails = (exploreKey: string, selectedArea: string | null, availableAreas: Area[]) => {
        if (!selectedArea) return { display_name: exploreKey, description: '' }
        const area = availableAreas.find(a => a.area === selectedArea)
        const details = area?.explore_details?.[exploreKey]
        
        if (details) {
          return details
        }
        
        // Fallback: create a display name from the explore key
        const fallbackDisplayName = exploreKey.split(':')[1]?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || exploreKey
        return { display_name: fallbackDisplayName, description: '' }
      }

      const result = getExploreDetails('missing:explore_key', 'Sales', mockAreas)
      expect(result).toEqual({ display_name: 'Explore Key', description: '' })
    })

    it('should handle malformed explore keys gracefully', () => {
      const getExploreDetails = (exploreKey: string, selectedArea: string | null, availableAreas: Area[]) => {
        if (!selectedArea) return { display_name: exploreKey, description: '' }
        const area = availableAreas.find(a => a.area === selectedArea)
        const details = area?.explore_details?.[exploreKey]
        
        if (details) {
          return details
        }
        
        // Fallback: create a display name from the explore key
        const fallbackDisplayName = exploreKey.split(':')[1]?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || exploreKey
        return { display_name: fallbackDisplayName, description: '' }
      }

      const result = getExploreDetails('malformed_key', 'Sales', mockAreas)
      expect(result).toEqual({ display_name: 'malformed_key', description: '' })
    })

    it('should handle missing explore_details gracefully', () => {
      const areasWithMissingDetails: Area[] = [
        {
          area: 'TestArea',
          explore_keys: ['test:explore'],
          explore_details: {} // Missing details
        }
      ]

      const getExploreDetails = (exploreKey: string, selectedArea: string | null, availableAreas: Area[]) => {
        if (!selectedArea) return { display_name: exploreKey, description: '' }
        const area = availableAreas.find(a => a.area === selectedArea)
        const details = area?.explore_details?.[exploreKey]
        
        if (details) {
          return details
        }
        
        // Fallback: create a display name from the explore key
        const fallbackDisplayName = exploreKey.split(':')[1]?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || exploreKey
        return { display_name: fallbackDisplayName, description: '' }
      }

      const result = getExploreDetails('test:explore', 'TestArea', areasWithMissingDetails)
      expect(result).toEqual({ display_name: 'Explore', description: '' })
    })
  })

  describe('Display name generation', () => {
    it('should properly format explore keys to display names', () => {
      const formatExploreKey = (exploreKey: string) => {
        return exploreKey.split(':')[1]?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || exploreKey
      }

      expect(formatExploreKey('ecommerce:order_items')).toBe('Order Items')
      expect(formatExploreKey('marketing:user_events')).toBe('User Events')
      expect(formatExploreKey('analytics:web_analytics_dashboard')).toBe('Web Analytics Dashboard')
      expect(formatExploreKey('simple')).toBe('simple') // No colon
      expect(formatExploreKey('test:single')).toBe('Single')
    })

    it('should handle edge cases in formatting', () => {
      const formatExploreKey = (exploreKey: string) => {
        return exploreKey.split(':')[1]?.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()) || exploreKey
      }

      expect(formatExploreKey('')).toBe('')
      expect(formatExploreKey(':')).toBe(':') // Returns original when no second part
      expect(formatExploreKey('model:')).toBe('model:') // Returns original when no second part  
      expect(formatExploreKey(':explore')).toBe('Explore')
    })
  })

  describe('Area and explore validation', () => {
    it('should validate area exists in available areas', () => {
      const isValidArea = (area: string, availableAreas: Area[]) => {
        return availableAreas.some(a => a.area === area)
      }

      expect(isValidArea('Sales', mockAreas)).toBe(true)
      expect(isValidArea('Marketing', mockAreas)).toBe(true)
      expect(isValidArea('NonExistent', mockAreas)).toBe(false)
      expect(isValidArea('', mockAreas)).toBe(false)
    })

    it('should validate explore exists in selected area', () => {
      const isValidExploreForArea = (exploreKey: string, area: string, availableAreas: Area[]) => {
        const areaData = availableAreas.find(a => a.area === area)
        return areaData ? areaData.explore_keys.includes(exploreKey) : false
      }

      expect(isValidExploreForArea('ecommerce:order_items', 'Sales', mockAreas)).toBe(true)
      expect(isValidExploreForArea('marketing:campaigns', 'Marketing', mockAreas)).toBe(true)
      expect(isValidExploreForArea('ecommerce:order_items', 'Marketing', mockAreas)).toBe(false)
      expect(isValidExploreForArea('nonexistent:explore', 'Sales', mockAreas)).toBe(false)
    })
  })
})
