import {
  Aside,
  Button,
  ButtonTransparent,
  FieldTextArea,
  Heading,
  Icon,
  Layout,
  Section,
  Space,
  SpaceVertical,
  Span,
  Spinner,
} from '@looker/components'
import React, { FormEvent, useCallback, useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { RootState } from '../../store'
import useSendVertexMessage from '../../hooks/useSendVertexMessage'
import SamplePrompts from '../../components/SamplePrompts'
import {
  addMessage,
  resetChat,
  setExploreUrl,
  setIsQuerying,
  setQuery,
} from '../../slices/assistantSlice'
import Chat from '../../components/Chat'
import { ArrowBackIosSharp } from '@material-ui/icons'
import GeminiLogo from '../../components/GeminiLogo'
import { ExploreEmbed } from '../../components/ExploreEmbed'
import { useLookerFields } from '../../hooks/useLookerFields'
import { useBigQueryExamples } from '../../hooks/useBigQueryExamples'

const ExploreChatPage = () => {
  const dispatch = useDispatch()
  const [loading, setLoading] = React.useState<boolean>(true)
  const [isQueryPending, setIsQueryPending] = React.useState<boolean>(false)
  const { isQuerying, exploreUrl, query, dimensions, measures, examples } =
    useSelector((state: RootState) => state.assistant)
  const [textAreaValue, setTextAreaValue] = React.useState<string>(query)

  const { generateExploreUrl } = useSendVertexMessage()

  // load dimensions, measures and examples into the state
  useLookerFields()
  useBigQueryExamples()

  useEffect(() => {
    if (
      dimensions.length > 0 &&
      measures.length > 0 &&
      examples.exploreGenerationExamples.length > 0 &&
      examples.exploreRefinementExamples.length > 0
    ) {
      setLoading(false)
    }
  }, [dimensions, measures, examples])

  useEffect(() => {
    if (query.trim() === '') return
    if (isQuerying) return

    generateExploreUrl(query)
  }, [query])

  useEffect(() => {
    if (isQueryPending) {
      setIsQueryPending(false)
      handleExploreSubmit()
    }
  }, [isQueryPending])

  const handleExploreSubmit = useCallback(async () => {
    if (textAreaValue.trim() === '') return
    const query = textAreaValue.trim()

    dispatch(setIsQuerying(true))
    dispatch(setQuery(query))
    dispatch(setExploreUrl(''))

    const newExploreUrl = await generateExploreUrl(query)

    dispatch(
      addMessage({
        type: 'explore',
        actor: 'system',
        exploreUrl: newExploreUrl,
        createdAt: Date.now(),
        summarizedPrompt: query,
      }),
    )

    dispatch(setExploreUrl(newExploreUrl))
    dispatch(setIsQuerying(false))
  }, [textAreaValue])

  const handlePromptSubmit = (prompt: string) => {
    dispatch(setQuery(prompt))
    setTextAreaValue(prompt)
    setIsQueryPending(true)
  }

  const handleChange = (e: FormEvent<HTMLTextAreaElement>) => {
    setTextAreaValue(e.currentTarget.value)
  }

  const reset = () => {
    dispatch(resetChat())
    setTextAreaValue('')
  }

  return (
    <Layout height={'100%'} hasAside={true}>
      {loading ? (
        <Spinner color="key" />
      ) : (
        <>
          <Section>
            {exploreUrl != '' ? (
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
              {exploreUrl && (
                <ButtonTransparent onClick={reset}>
                  <Icon icon={<ArrowBackIosSharp />} size={20} />
                  <Span>Back</Span>
                </ButtonTransparent>
              )}
            </Space>
            {exploreUrl ? (
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
                    onKeyDown={(e) =>
                      e.key === 'Enter' && handleExploreSubmit()
                    }
                    onChange={handleChange}
                    disabled={isQuerying}
                  />

                  <Button
                    my={'u6'}
                    disabled={isQuerying}
                    onClick={handleExploreSubmit}
                  >
                    Generate Explore
                  </Button>
                </Section>

                <SamplePrompts handleSubmit={handlePromptSubmit} />
              </SpaceVertical>
            )}
          </Aside>
        </>
      )}
    </Layout>
  )
}

export default ExploreChatPage
