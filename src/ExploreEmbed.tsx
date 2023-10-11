/*

 Copyright 2023 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

 */

 import React, { useContext, useRef, useEffect } from 'react'
 import styled from 'styled-components'
 import { LookerEmbedSDK } from '@looker/embed-sdk'
 import { ExtensionContext } from '@looker/extension-sdk-react'
 const LOOKER_EXPLORE_ID = process.env.LOOKER_EXPLORE_ID || ''
 
 export interface ExploreEmbedProps {
   exploreUrl: string,
   setExplore: any,
   setSubmit: any
 }
 
 export const ExploreEmbed = ({ exploreUrl, setExplore, setSubmit }: ExploreEmbedProps) => {
   const { extensionSDK } = useContext(ExtensionContext)
 
   // eslint-disable-next-line @typescript-eslint/no-explicit-any
   const canceller = (event: any) => {
     return { cancel: !event.modal }
   }
 
   const ref = useRef<HTMLDivElement>(null)
 
   const animateExploreLoad = () => {
     setSubmit(false)
     document.getElementById('embedcontainer')?.style.setProperty('opacity', '1')
   }
 
   useEffect(() => {
     const hostUrl = extensionSDK?.lookerHostData?.hostUrl
     const el = ref.current
     if (el && hostUrl && exploreUrl) {
       let paramsObj:any = {
            'embed_domain': window.origin,
            'sdk': '2',
            '_theme': JSON.stringify({
              key_color: '#174ea6',
              background_color: '#f4f6fa',
            })
       }
       exploreUrl.split("&").map((param) => 
        paramsObj[param.split("=")[0]] = param.split("=")[1]
       )
       el.innerHTML = ''
       LookerEmbedSDK.init(hostUrl)
      //  LookerEmbedSDK.createExploreWithId('sfdc_demo/opportunity_line_item')
       LookerEmbedSDK.createExploreWithId(LOOKER_EXPLORE_ID)
         .appendTo(el)
         .withClassName('looker-embed')
         .withParams(paramsObj)
         .on('drillmenu:click', canceller)
         .on('drillmodal:explore', canceller)
         .on('explore:run:start', animateExploreLoad)
         .on('explore:run:complete', (e) => console.log(e))
         .build()
         .connect()
         .then((explore)=> setExplore(explore))
         .catch((error: Error) => {
           // @TODO - This should probably throw a visible error
           // eslint-disable-next-line no-console
           console.error('Connection error', error)
         })
     }
     // eslint-disable-next-line react-hooks/exhaustive-deps
   }, [exploreUrl])
 
   return <EmbedContainer id='embedcontainer' ref={ref} />
 }
 
 const EmbedContainer = styled.div`
   backgroundColor: #f7f7f7;
   height: 100%;
   opacity: 0.2;
   animation: fadeIn ease-in ease-out 3s;
   > iframe {
     display: block;
     backgroundColor: #f7f7f7;
     height: 100%;
     width: 100%;
   }
 `
 