import React, { useContext } from 'react'

import Message from './Message'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useDispatch } from 'react-redux'

import { ExploreParams, setSidePanelExploreParams } from '../../slices/assistantSlice'
import { ExploreHelper } from '../../utils/ExploreHelper'

import {
  openSidePanel,
} from '../../slices/assistantSlice'
import { OpenInNew } from '@material-ui/icons'

interface ExploreMessageProps {
  exploreId: string
  modelName: string
  prompt: string
  exploreParams: ExploreParams
  autoOpen: boolean
  emojis?: string[]
  fields?: string[]
  isLoading?: boolean
  summary?: string
}

export default function ExploreMessage({
  modelName,
  exploreId,
  prompt,
  exploreParams,
  autoOpen, // You can keep this prop for backward compatibility
  emojis,
  fields,
  isLoading,
  summary,
}: ExploreMessageProps) {
  const dispatch = useDispatch()
  const { extensionSDK } = useContext(ExtensionContext)

  const exploreHref = `/explore/${modelName}/${exploreId}?${ExploreHelper.exploreQueryArgumentString(exploreParams)}&toggle=vis,data`
  const openExplore = () => {
    extensionSDK.openBrowserWindow(exploreHref, '_blank')
  }

  const openSidePanelExplore = () => {
    dispatch(setSidePanelExploreParams(exploreParams))
    dispatch(openSidePanel())
  }

  return (
    <>
      <Message actor="system" createdAt={Date.now()}>
        <div>
          {summary && (
            <div className="mb-3 p-3 bg-blue-50 border-l-4 border-blue-400 text-blue-800 text-sm rounded">
              <div className="font-medium mb-1">
                {summary.toLowerCase().includes('note') ? 'Note:' : 
                 summary.toLowerCase().includes('analysis') ? 'Analysis:' :
                 summary.toLowerCase().includes('insight') ? 'Insight:' :
                 summary.toLowerCase().includes('context') ? 'Context:' :
                 'Summary:'}
              </div>
              <div>{summary}</div>
            </div>
          )}
          <div
            className="bg-gray-400 text-white rounded-md p-4 my-2 shadow-lg hover:bg-gray-500 cursor-pointer"
            onClick={openSidePanelExplore}
          >
            <div className="flex flex-row text-md font-semibold">
              <div className="flex-grow">Explore</div>
            </div>
            <div className="text-xs mt-2 line-clamp-3">{prompt}</div>
          </div>
          <div
            className="cursor-pointer hover:underline text-sm text-blue-500 flex flex-col justify-center items-end"
            onClick={openExplore}
          >
            <div>visit <OpenInNew fontSize={'small'} /></div>
          </div>
        </div>
      </Message>
    </>
  )
}
