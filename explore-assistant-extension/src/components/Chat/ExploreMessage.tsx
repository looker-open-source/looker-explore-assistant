import React from 'react'

import Message from './Message'
import { Link } from '@looker/components'
import { useContext } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../../store'
import {
  openSidePanel,
  setSidePanelExploreUrl,
} from '../../slices/assistantSlice'
import { Explore, OpenInNew, Share } from '@material-ui/icons'

interface ExploreMessageProps {
  prompt: string
  queryArgs: string
}

const ExploreMessage = ({ prompt, queryArgs }: ExploreMessageProps) => {
  const dispatch = useDispatch()
  const { exploreId } = useSelector((state: RootState) => state.assistant)
  const { extensionSDK } = useContext(ExtensionContext)
  const exploreHref = `/explore/${exploreId}?${queryArgs}`
  const openExplore = () => {
    extensionSDK.openBrowserWindow(exploreHref, '_blank')
  }

  const openSidePanelExplore = () => {
    dispatch(setSidePanelExploreUrl(queryArgs))
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
