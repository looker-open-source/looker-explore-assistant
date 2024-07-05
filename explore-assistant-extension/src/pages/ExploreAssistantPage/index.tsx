import {
  Aside,
  Box,
  Button,
  FieldTextArea,
  Heading,
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
import process from 'process'
import {
  addToHistory,
  setExploreUrl,
  setHistory,
  setIsQuerying,
  setQuery,
  setExploreId,
  setExploreName,
  setModelName,
} from '../../slices/assistantSlice'
import SamplePrompts from '../../components/SamplePrompts'
import ExploreSelect from '../../components/ExploreSelect'
import PromptHistory from '../../components/PromptHistory'
import { RootState } from '../../store'
import useFetchData from '../../hooks/useSendVertexMessage'
import ExploreBasePage from '../ExploreBasePage/'

const ExploreAssistantPage = () => {
  const dispatch = useDispatch()
  const { generateExploreUrl } = useFetchData()
  const [textAreaValue, setTextAreaValue] = React.useState<string>('')
  const { extensionSDK } = useContext(ExtensionContext)
  const APPLICATION_NAME = process.env.APPLICATION_NAME || 'Explore Assistant'

  const {
    exploreUrl,
    isQuerying,
    history,
    examples,
    exploreId, // Added exploreId to selector
  } = useSelector((state: RootState) => state.assistant)

  // Fetch the chat history from local storage on startup and when exploreId changes
  useEffect(() => {
    const fetchHistory = async () => {
      const key = `chat_history_${exploreId}`
      const responses = await extensionSDK.localStorageGetItem(key)
      if (responses === null) {
        dispatch(setHistory([])) // Clear history if no data in local storage
        return
      }
      const data = JSON.parse(responses)
      const localStorageHistory = []
      for (const [key, value] of Object.entries(data)) {
        if (key === '' || typeof value !== 'object' || value == null) {
          continue
        }
        if (value['url'] === undefined || value['message'] === undefined) {
          continue
        }
        localStorageHistory.push({
          message: value['message'],
          url: value['url'],
        })
      }
      dispatch(setHistory(localStorageHistory))
    }
    if (exploreId) {
      fetchHistory()
    } else {
      dispatch(setHistory([])) // Clear history if no exploreId
    }
  }, [exploreId]) // Fetch history when exploreId changes

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
      const key = `chat_history_${exploreId}`
      await extensionSDK.localStorageSetItem(
        key,
        JSON.stringify(updatedHistory),
      )
    },
    [history, examples, exploreId], // Added exploreId to dependencies
  )

  const handleSubmit = useCallback(async () => {
    handleExploreUrl(textAreaValue)
  }, [textAreaValue, handleExploreUrl])

  const handleChange = (e: FormEvent<HTMLTextAreaElement>) => {
    setTextAreaValue(e.currentTarget.value)
  }

  const handlePromptSubmit = (prompt: string) => {
    setTextAreaValue(prompt)
    handleExploreUrl(prompt)
  }

  const handleSelect = (value: string) => {
    const exploreId = value.replace(':', '/')
    const modelName = value.split(':')[0]
    const exploreName = value.split(':')[1]
    dispatch(setExploreId(exploreId))
    dispatch(setModelName(modelName))
    dispatch(setExploreName(exploreName))
    dispatch(setHistory([])) // Clear history immediately when exploreId changes
    setTextAreaValue('') // Clear the FieldTextArea
  }

  return (
    <ExploreBasePage>
      <Aside
        paddingX={'u8'}
        paddingY={'u4'}
        minWidth={'400px'}
        borderRight={'key'}
      >
        <Heading fontSize={'xxlarge'} fontWeight={'semiBold'}>
          {APPLICATION_NAME}
        </Heading>
        <Paragraph fontSize={'small'}>
          Pick a data domain and inquire with the help of the Gemini model on
          Vertex AI.
        </Paragraph>
        <Box py="u4">
          <ExploreSelect handleSelect={handleSelect} />
        </Box>
        <FieldTextArea
          label="Type your prompt in here"
          description="💡 Tip: Try asking for your data output in a viz!"
          value={textAreaValue}
          onKeyDown={(e: any) => {
            // nativeEvent.code check to determine if enter press is for submission or for accepting japanese kanji character
            if (e.key === 'Enter' && e.keyCode !== 229) {
              handleSubmit()
            }
          }}
          onChange={handleChange}
          disabled={isQuerying}
        />
        <Button my={'u6'} disabled={isQuerying} onClick={() => handleSubmit()}>
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
        {exploreUrl !== '' ? (
          <ExploreEmbed />
        ) : (
          <Space height="100%" width="100%" align={'center'} justify={'center'}>
            <GeminiLogo width={'300px'} animate={isQuerying} />
          </Space>
        )}
      </Section>
    </ExploreBasePage>
  )
}

export default ExploreAssistantPage
