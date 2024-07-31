import React from 'react'

import Message from './Message'
import {
  Box,
  Chip,
  Icon,
  Link,
  Paragraph,
  Section,
  Space,
  Tooltip,
} from '@looker/components'
import { useContext } from 'react'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../../store'
import { Info } from '@material-ui/icons'
import {
  openSidePanel,
  setSidePanelExploreUrl,
} from '../../slices/assistantSlice'

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
        <Box my={'u2'}>
          <Space between style={{ position: 'relative' }}>
            <div onClick={openSidePanelExplore}>
              <Chip disabled>Explore</Chip>
            </div>
            {prompt && (
              <Box position="absolute" right="-10px" top="0px" cursor="pointer">
                <Tooltip content={prompt}>
                  <Icon color={'ui3'} size="xxsmall" icon={<Info />} />
                </Tooltip>
              </Box>
            )}
          </Space>
        </Box>
        <Section>
          <Paragraph>Here is the link to your explore:</Paragraph>
          <Box mb="u4">
            <Link href="#" onClick={openExplore} isExternal>
              Visit Explore
            </Link>
          </Box>
        </Section>
      </Message>
    </>
  )
}

export default ExploreMessage
