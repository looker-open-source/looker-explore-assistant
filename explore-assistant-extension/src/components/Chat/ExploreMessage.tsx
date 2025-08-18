import React, { useContext } from 'react'

import Message from './Message'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useDispatch } from 'react-redux'
import FeedbackButton from '../Feedback/FeedbackButton'

import { ExploreParams, setSidePanelExploreParams, VectorSearchSummaryInfo } from '../../slices/assistantSlice'
import { ExploreHelper } from '../../utils/ExploreHelper'

import {
  openSidePanel,
} from '../../slices/assistantSlice'
import { OpenInNew, Search, FindInPage } from '@material-ui/icons'

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
  vectorSearchSummary?: VectorSearchSummaryInfo
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
  vectorSearchSummary,
}: ExploreMessageProps) {
  const dispatch = useDispatch()
  const { extensionSDK } = useContext(ExtensionContext)

  const exploreHref = `/explore/${modelName}/${exploreId}?${ExploreHelper.exploreQueryArgumentString(exploreParams)}&toggle=vis,data`
  const shareUrl = typeof window !== 'undefined' ? `${window.location.origin}${exploreHref}` : exploreHref
  
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
          
          {/* Vector Search Usage Notification */}
          {vectorSearchSummary && vectorSearchSummary.total_vector_searches > 0 && (
            <div className="mb-3 p-3 bg-purple-50 border-l-4 border-purple-400 text-purple-800 text-sm rounded">
              <div className="flex items-center font-medium mb-1">
                <Search className="mr-2" fontSize="small" />
                Smart Data Discovery Used
              </div>
              <div className="text-xs space-y-1">
                {vectorSearchSummary.user_messages.map((message, idx) => (
                  <div key={idx} className="flex items-center">
                    <FindInPage className="mr-1" fontSize="small" />
                    {message}
                  </div>
                ))}
                <div className="text-purple-600 mt-1">
                  ({vectorSearchSummary.total_vector_searches} smart {vectorSearchSummary.total_vector_searches === 1 ? 'search' : 'searches'} performed)
                </div>
              </div>
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
          
          {/* Add feedback buttons for user interaction */}
          <div className="mt-3 flex justify-end">
            <FeedbackButton
              exploreId={`${modelName}:${exploreId}`}
              originalPrompt={prompt}
              generatedParams={exploreParams}
              shareUrl={shareUrl}
              size="small"
              onFeedbackSubmitted={(feedbackType, success) => {
                console.log(`Feedback ${feedbackType} submitted:`, success)
              }}
            />
          </div>
        </div>
      </Message>
    </>
  )
}
