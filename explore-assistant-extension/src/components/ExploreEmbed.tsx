/*

MIT License

Copyright (c) 2023 Looker Data Sciences, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

import React, { useContext, useRef, useEffect, useCallback } from 'react'
import styled from 'styled-components'
import { LookerEmbedSDK } from '@looker/embed-sdk'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { ExploreHelper } from '../utils/ExploreHelper'
import { ExploreParams } from '../slices/assistantSlice'
import { useCheckForConnectionFailure } from '../hooks/useCheckForConnectionFailure'
import objectHash from 'object-hash'

export interface ExploreEmbedProps {
  modelName: string | null | undefined
  exploreId: string | null | undefined
  exploreParams: ExploreParams
}

export const ExploreEmbed = ({
  modelName,
  exploreId,
  exploreParams,
}: ExploreEmbedProps) => {
  
  // Generate a unique key for the embed container to force remount on param changes
  const embedKey = modelName && exploreId && exploreParams
    ? `${modelName}_${exploreId}_${objectHash(exploreParams)}`
    : 'empty-embed'

  if (!modelName || !exploreId || !exploreParams) {
    return <></>
  }

  const { extensionSDK } = useContext(ExtensionContext)
  const [exploreRunStart, setExploreRunStart] = React.useState(false)
  const { settings } = useSelector((state: RootState) => state.assistant)

  // Initialize connection failure detection hook
  const {
    isConnecting,
    connectionError,
    retryCount,
    hasReachedMaxRetries,
    handleError,
    handleConnectionSuccess,
    setConnecting,
    resetConnectionState,
    isDatabaseConnectionError,
  } = useCheckForConnectionFailure({
    maxRetries: 3,
    retryDelay: 2000,
    openAccountsPageOnFailure: true,
    customFailureHandler: (info) => {
      console.warn('ExploreEmbed: Connection failure detected', info)
      // Could dispatch to Redux store or show toast notification here
    },
    enableLogging: true,
  })

  const canceller = (event: any) => {
    return { cancel: !event.modal }
  }

  const ref = useRef<HTMLDivElement>(null)

  // Cleanup effect to clear the container and any SDK state on unmount or before new embed
  useEffect(() => {
    return () => {
      if (ref.current) {
        ref.current.innerHTML = ''
      }
    }
  }, [embedKey])

  const handleQueryError = () => {
    setTimeout(() => !exploreRunStart && animateExploreLoad(), 10)
  }

  const animateExploreLoad = () => {
    document.getElementById('embedcontainer')?.style.setProperty('opacity', '1')
  }

  const setExploreLoading = (_explore: any) => {}

  // Enhanced connection function with retry logic
  const connectToExplore = useCallback(async (retryAttempt = 0) => {
    const hostUrl = extensionSDK?.lookerHostData?.hostUrl
    const el = ref.current
    
    if (!el || !hostUrl || !exploreParams) {
      console.warn('ExploreEmbed: Missing required elements for connection', {
        hasElement: !!el,
        hasHostUrl: !!hostUrl,
        hasExploreParams: !!exploreParams
      })
      return
    }

    setConnecting(true)

    const paramsObj: any = {
      // For Looker Original use window.origin for Looker Core use hostUrl
      embed_domain: hostUrl, //window.origin, //hostUrl,
      sdk: '2',
      _theme: JSON.stringify({
        key_color: '#174ea6',
        background_color: '#f4f6fa',
      }),
      toggle: 'pik,vis,dat',
    }

    if (settings['show_explore_data'].value) {
      paramsObj['toggle'] = 'pik,vis'
    }

    const encodedParams = ExploreHelper.encodeExploreParams(exploreParams)
    for (const key in encodedParams) {
      paramsObj[key] = encodedParams[key]
    }

    try {
      el.innerHTML = ''
      LookerEmbedSDK.init(hostUrl)
      
      const explore = await LookerEmbedSDK.createExploreWithId(modelName + '/' + exploreId)
        .appendTo(el)
        .withClassName('looker-embed')
        .withParams(paramsObj)
        .on('explore:ready', () => handleQueryError())
        .on('drillmenu:click', canceller)
        .on('drillmodal:explore', canceller)
        .on('explore:run:start', () => {
          setExploreRunStart(true)
          animateExploreLoad()
        })
        .on('explore:run:complete', () => setExploreRunStart(false))
        .build()
        .connect()

      console.log('ExploreEmbed - Successfully connected to explore:', explore)
      
      handleConnectionSuccess()
      setExploreLoading(explore)
      
    } catch (error: any) {
      console.error('ExploreEmbed - Error details:', {
        message: error.message,
        stack: error.stack,
        hostUrl,
        modelName,
        exploreId,
        exploreParams,
        retryAttempt
      })

      const shouldRetry = handleError(error, {
        modelName: modelName || undefined,
        exploreId: exploreId || undefined,
        hostUrl,
        queryUrl: `${hostUrl}/embed/explore/${modelName}/${exploreId}`
      })

      // If should retry and we haven't reached max retries, schedule a retry
      if (shouldRetry && !hasReachedMaxRetries) {
        console.log(`ExploreEmbed - Scheduling retry ${retryCount + 1}`)
        setTimeout(() => {
          connectToExplore(retryAttempt + 1)
        }, 2000) // 2 second delay between retries
      } else {
        setConnecting(false)
      }
    }
  }, [
    extensionSDK,
    exploreParams,
    modelName,
    exploreId,
    settings,
    handleError,
    handleConnectionSuccess,
    setConnecting,
    hasReachedMaxRetries,
    retryCount
  ])

  useEffect(() => {
    // Reset connection state when exploreParams change (new query URL)
    resetConnectionState()
    connectToExplore()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exploreParams])

  if (!exploreParams || Object.keys(exploreParams).length === 0) {
    console.log('ExploreEmbed final check - returning empty due to no exploreParams:', {
      exploreParams,
      hasExploreParams: !!exploreParams,
      keysLength: exploreParams ? Object.keys(exploreParams).length : 'null'
    })
    return <></>
  }
  
  return (
    <>
      <EmbedContainer id="embedcontainer" ref={ref} key={embedKey} />

      {connectionError && hasReachedMaxRetries && (
        <ErrorStatus>
          {isDatabaseConnectionError(connectionError.error) ? (
            <>
              Database connection failed after multiple attempts.
              <br />
              Please check your connection settings in the accounts page.
              <br />
              <small>Error: {connectionError.error.message}</small>
            </>
          ) : (
            <>
              Failed to connect to Looker Explore after multiple attempts.
              <br />
              Error: {connectionError.error.message}
            </>
          )}
        </ErrorStatus>
      )}
    </>
  )
}

const EmbedContainer = styled.div<{}>`
  backgroundcolor: #f7f7f7;
  width: 100%;
  height: 100%;
  animation: fadeIn ease-in ease-out 3s;
  > iframe {
    width: 100%;
    height: 100%;
    display: block;
    backgroundcolor: #f7f7f7;
  }
`

const ConnectionStatus = styled.div`
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(23, 78, 166, 0.9);
  color: white;
  padding: 16px 24px;
  border-radius: 8px;
  text-align: center;
  font-size: 14px;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
`

const ErrorStatus = styled.div`
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(220, 53, 69, 0.9);
  color: white;
  padding: 16px 24px;
  border-radius: 8px;
  text-align: center;
  font-size: 14px;
  z-index: 1000;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-width: 400px;
  line-height: 1.4;
`
