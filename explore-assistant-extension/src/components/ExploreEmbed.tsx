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

import React, { useContext, useRef, useEffect } from 'react'
import styled from 'styled-components'
import { LookerEmbedSDK } from '@looker/embed-sdk'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useSelector } from 'react-redux'
import { RootState } from '../store'
import { ExploreHelper } from '../utils/ExploreHelper'
import { ExploreParams } from '../slices/assistantSlice'

export interface ExploreEmbedProps {
  exploreParams: ExploreParams
}


export const ExploreEmbed = ({ exploreParams }: ExploreEmbedProps) => {
  const { extensionSDK } = useContext(ExtensionContext)
  const [exploreRunStart, setExploreRunStart] = React.useState(false)

  const { exploreId, settings } = useSelector((state: RootState) => state.assistant)

  const canceller = (event: any) => {
    return { cancel: !event.modal }
  }

  const ref = useRef<HTMLDivElement>(null)

  const handleQueryError = () => {
    setTimeout(() => !exploreRunStart && animateExploreLoad(), 10)
  }

  const animateExploreLoad = () => {
    document.getElementById('embedcontainer')?.style.setProperty('opacity', '1')
  }

  const setExploreLoading = (_explore: any) => {}

  useEffect(() => {
    const hostUrl = extensionSDK?.lookerHostData?.hostUrl
    const el = ref.current
    if (el && hostUrl && exploreParams) {

      const paramsObj: any = {
        // For Looker Original use window.origin for Looker Core use hostUrl
        embed_domain: hostUrl, //window.origin, //hostUrl,
        sdk: '2',
        _theme: JSON.stringify({
          key_color: '#174ea6',
          background_color: '#f4f6fa',
        }),
        toggle: 'pik,vis',
      }

      let toggleString = '&toggle=dat,pik,vis'
      if(settings['show_explore_data'].value) {
        toggleString = '&toggle=pik,vis'
      }
      
      const finalParams: { [key: string]: string } = {};
      for (const key in exploreParams) {
        if (exploreParams.hasOwnProperty(key)) {
          if (key.includes('filter_config') || key.includes('vis') || key.includes('fields') 
              || key.startsWith('f[')) {
            finalParams[key] = exploreParams[key]; // Do not re-encode JSON params, fields, or filters
          } else {
            finalParams[key] = encodeURIComponent(exploreParams[key]).replace(/%20/g, ' ')
          }
        }
      }

      el.innerHTML = ''
      LookerEmbedSDK.init(hostUrl)
      LookerEmbedSDK.createExploreWithId(exploreId)
        .appendTo(el)
        .withClassName('looker-embed')
        .withParams(finalParams)
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
        .then((explore) => setExploreLoading(explore))
        .catch((error: Error) => {
          // @TODO - This should probably throw a visible error
          // eslint-disable-next-line no-console
          console.error('Connection error', error)
        })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exploreParams])

  return (
    <>
      <EmbedContainer id="embedcontainer" ref={ref} />
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
