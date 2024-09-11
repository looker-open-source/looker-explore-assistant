import React from 'react'

import Message from './Message'
import { useContext } from 'react'
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
}

const ExploreMessage = ({ modelName, exploreId, prompt, exploreParams }: ExploreMessageProps) => {
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
          <div className="mb-2">Here is the explore we generated.</div>
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

export default ExploreMessage
