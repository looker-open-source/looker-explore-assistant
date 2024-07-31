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

export interface ExploreEmbedProps {
  exploreUrl: string
}

export const ExploreEmbed = ({ exploreUrl }: ExploreEmbedProps) => {
  const { extensionSDK } = useContext(ExtensionContext)
  const [exploreRunStart, setExploreRunStart] = React.useState(false)

  const { exploreId } = useSelector((state: RootState) => state.assistant)

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
    if (el && hostUrl && exploreUrl) {
      const paramsObj: any = {
        // For Looker Original use window.origin for Looker Core use hostUrl
        embed_domain: hostUrl, //window.origin, //hostUrl,
        sdk: '2',
        _theme: JSON.stringify({
          key_color: '#174ea6',
          background_color: '#f4f6fa',
        }),
      }
      exploreUrl.split('&').map((param) => {
        const [key, ...rest] = param.split('=')
        // paramsObj[key] = rest.join('=')
        if (key === 'filter_expression' || key === 'dynamic_fields') {
          // console.log('rest', rest)
          paramsObj[key] = rest.join('=')
        } else {
          paramsObj[key] = param.split('=')[1]
        }
      })
      el.innerHTML = ''
      LookerEmbedSDK.init(hostUrl)
      LookerEmbedSDK.createExploreWithId(exploreId)
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
        .then((explore) => setExploreLoading(explore))
        .catch((error: Error) => {
          // @TODO - This should probably throw a visible error
          // eslint-disable-next-line no-console
          console.error('Connection error', error)
        })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exploreUrl])

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
