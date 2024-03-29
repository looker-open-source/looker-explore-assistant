import {
  Aside,
  Button,
  FieldTextArea,
  Heading,
  Layout,
  Paragraph,
  Section,
  Space,
  Tab2,
  Tabs2,
} from '@looker/components'
import React, { FormEvent, useCallback, useContext, useEffect } from 'react'
import { ExploreEmbed } from '../../components/ExploreEmbed'
import GeminiLogo from '../../components/GeminiLogo'
import { ExtensionContext } from '@looker/extension-sdk-react'
import { useDispatch, useSelector } from 'react-redux'
import {
  addToHistory,
  setExploreUrl,
  setHistory,
  setIsQuerying,
  setQuery,
} from '../../slices/assistantSlice'
import SamplePrompts from '../../components/SamplePrompts'
import PromptHistory from '../../components/PromptHistory'
import { RootState } from '../../store'
import useFetchData from '../../hooks/useSendVertexMessage'
import { useLookerFields } from '../../hooks/useLookerFields'
import { useBigQueryExamples } from '../../hooks/useBigQueryExamples'

const ExploreAssistantPage = () => {
  const dispatch = useDispatch()
  const { generateExploreUrl } = useFetchData()
  const [textAreaValue, setTextAreaValue] = React.useState<string>('')
  const { extensionSDK } = useContext(ExtensionContext)

  const { exploreUrl, isQuerying, history } = useSelector(
    (state: RootState) => state.assistant,
  )

  // load dimensions and measures into the state
  useLookerFields()
  useBigQueryExamples()

  // fetch the chat history from local storage on startup
  useEffect(() => {
    extensionSDK.localStorageGetItem('chat_history').then((responses) => {
      if (responses === null) {
        return
      }
      const data = JSON.parse(responses)
      const localStorageHistory = []
      for (const [key, value] of Object.entries(data)) {
        if (key == '' || typeof value != 'object' || value == null) {
          continue
        }
        if (value['url'] == undefined || value['message'] == undefined) {
          continue
        }
        localStorageHistory.push({
          message: value['message'],
          url: value['url'],
        })
      }
      dispatch(setHistory(localStorageHistory))
    })
  }, [])

  const handleExploreUrl = useCallback(
    async (query: string) => {
      dispatch(setIsQuerying(true))
      dispatch(setQuery(query))
      dispatch(setExploreUrl(''))

      const newExploreUrl = await generateExploreUrl(query)

      dispatch(setExploreUrl(newExploreUrl))
      dispatch(setIsQuerying(false))

      const newHistoryItem = { message: query, url: newExploreUrl }
      dispatch(addToHistory(newHistoryItem))
      const updatedHistory = [...history, newHistoryItem]
      await extensionSDK.localStorageSetItem(
        `chat_history`,
        JSON.stringify(updatedHistory),
      )
    },
    [history],
  )

  const handleSubmit = useCallback(async () => {
    handleExploreUrl(textAreaValue)
  }, [textAreaValue])

  const handleChange = (e: FormEvent<HTMLTextAreaElement>) => {
    setTextAreaValue(e.currentTarget.value)
  }

  const handlePromptSubmit = (prompt: string) => {
    setTextAreaValue(prompt)
    handleExploreUrl(prompt)
  }

  return (
    <>
      <Layout height={'100%'} hasAside={true}>
        <Aside
          paddingX={'u8'}
          paddingY={'u4'}
          minWidth={'400px'}
          borderRight={'key'}
        >
          <Heading fontSize={'xxlarge'} fontWeight={'semiBold'}>
            Explore Assistant
          </Heading>
          <Paragraph fontSize={'small'} marginBottom={'u4'}>
            Ask questions of a sample Ecommerce dataset powered by the Gemini
            model on Vertex AI.
          </Paragraph>
          <FieldTextArea
            label="Type your prompt in here"
            description="💡 Tip: Try asking for your data output in a viz!"
            value={textAreaValue}
            onKeyDown={(e) => {
              // nativeEvent.code check to determine if enter press is for submission or for accepting japanese kanji character
              // console.log(e.nativeEvent)
              if(e.key === 'Enter' && e.keyCode !== 229 ) {
                handleSubmit()
              }
            }}
            onChange={handleChange}
            disabled={isQuerying}
          />
          <Button
            my={'u6'}
            disabled={isQuerying}
            onClick={() => handleSubmit()}
          >
            Run Prompt
          </Button>
          <Section>
            <Tabs2 defaultTabId="prompts" distributed>
              <Tab2 id="prompts" label="Sample Prompts">
                <SamplePrompts handleSubmit={handlePromptSubmit} />
              </Tab2>
              <Tab2 id="history" label="Your History">
                <PromptHistory handleSubmit={handlePromptSubmit} />
              </Tab2>
            </Tabs2>
          </Section>
        </Aside>
        <Section height="100%">
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
      </Layout>
    </>
  )
}

export default ExploreAssistantPage
