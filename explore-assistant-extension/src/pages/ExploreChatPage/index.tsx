import {
  Aside,
  Button,
  ButtonTransparent,
  FieldTextArea,
  Heading,
  Icon,
  Section,
  Space,
  SpaceVertical,
  Span,
} from '@looker/components'
import React, { FormEvent, useCallback, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../../store'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import SamplePrompts from '../../components/SamplePrompts'
import {
  addMessage,
  resetChat,
  setExploreParams,
  setIsQuerying,
  setQuery,
} from '../../slices/assistantSlice'
import Chat from '../../components/Chat'
import { ArrowBackIosSharp } from '@material-ui/icons'
import GeminiLogo from '../../components/GeminiLogo'
import { ExploreEmbed } from '../../components/ExploreEmbed'
import ExploreBasePage from '../ExploreBasePage/'

const ExploreChatPage = () => {
  const dispatch = useDispatch()
  const [isQueryPending, setIsQueryPending] = React.useState<boolean>(false)
  const { isQuerying, exploreParams, query } =
    useSelector((state: RootState) => state.assistant)
  const [textAreaValue, setTextAreaValue] = React.useState<string>(query)

  const { generateExploreParams } = useSendVertexMessage()

  useEffect(() => {
    if (query.trim() === '') return
    if (isQuerying) return

    generateExploreParams(query)
  }, [query])

  useEffect(() => {
    if (isQueryPending) {
      setIsQueryPending(false)
      handleExploreSubmit()
    }
  }, [isQueryPending])

  const handleExploreSubmit = useCallback(async ( prompt? : string) => {
    let query = textAreaValue.trim()
    if(prompt) {
      query = prompt
    }

    if (!query || query.trim() === '') return

    dispatch(setIsQuerying(true))
    dispatch(setQuery(query))
    dispatch(setExploreParams(null))

    const newExploreParams = await generateExploreParams(query)

    dispatch(
      addMessage({
        type: 'explore',
        actor: 'system',
        exploreParams: newExploreParams,
        createdAt: Date.now(),
        summarizedPrompt: query,
      }),
    )

    dispatch(setExploreParams(newExploreParams))
    dispatch(setIsQuerying(false))
  }, [textAreaValue, generateExploreParams])

  const handleSamplePromptSubmit = (prompt: string) => {
    setTextAreaValue(prompt)
    handleExploreSubmit(prompt)
  }

  const handleChange = (e: FormEvent<HTMLTextAreaElement>) => {
    setTextAreaValue(e.currentTarget.value)
  }

  const reset = () => {
    dispatch(resetChat())
    setTextAreaValue('')
  }

  return (
    <ExploreBasePage>
        <>
          <Section>
            {exploreParams ? (
              <ExploreEmbed />
            ) : (
              <Space
                height="100%"
                width="100%"
                align={'center'}
                justify={'center'}
              >
                <GeminiLogo width={'300px'} animate={isQuerying} />
              </Space>
            )}
          </Section>
          <Aside
            paddingX={'u8'}
            paddingY={'u4'}
            minWidth={'400px'}
            borderLeft={'key'}
          >
            <Space between>
              <Heading fontSize={'xxlarge'} fontWeight={'semiBold'}>
                Explore Assistant
              </Heading>
              {exploreParams && (
                <ButtonTransparent onClick={reset}>
                  <Icon icon={<ArrowBackIosSharp />} size={20} />
                  <Span>Back</Span>
                </ButtonTransparent>
              )}
            </Space>
            {exploreParams ? (
              <SpaceVertical>
                <Space justify={'end'}></Space>
                <Chat />
              </SpaceVertical>
            ) : (
              <SpaceVertical mt={'u8'} gap={'none'}>
                <Section width={'100%'}>
                  <FieldTextArea
                    label="Type your prompt in here"
                    description="💡 Tip: Try asking for your data output in a viz!"
                    value={textAreaValue}
                    onKeyDown={(e:any) => {
                      // nativeEvent.code check to determine if enter press is for submission or for accepting japanese kanji character
                      if(e.key === 'Enter' && e.keyCode !== 229 ) {
                        handleExploreSubmit()
                      }
                    }}
                    onChange={handleChange}
                    disabled={isQuerying}
                  />

                  <Button
                    my={'u6'}
                    disabled={isQuerying}
                    onClick={() => handleExploreSubmit}
                  >
                    Generate Explore
                  </Button>
                </Section>

                <SamplePrompts handleSubmit={handleSamplePromptSubmit} />
              </SpaceVertical>
            )}
          </Aside>
        </>
    </ExploreBasePage>
  )
}

export default ExploreChatPage
