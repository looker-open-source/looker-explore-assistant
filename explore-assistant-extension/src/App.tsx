/*

MIT License

Copyright (c) 2023 Looker Data Sciences, Inc.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

*/

import React, { useContext, useEffect } from 'react'
import { hot } from 'react-hot-loader/root'
import {
  Button,
  Page,
  SpaceVertical,
  FieldTextArea,
  Tabs2,
  Tab2,
  Select,
} from '@looker/components'
import { ExtensionContext } from '@looker/extension-sdk-react'
import type { ChangeEvent } from 'react'
import { ExploreEmbed } from './ExploreEmbed'
import styles from './styles.module.css'
// import { initDB, addData, getStoreData, updateData, getData } from './db'

const VERTEX_AI_ENDPOINT = process.env.VERTEX_AI_ENDPOINT || ''
const LOOKER_MODEL = process.env.LOOKER_MODEL || ''
const LOOKER_EXPLORE = process.env.LOOKER_EXPLORE || ''

const ExploreAssistant = () => {
  const { core40SDK, extensionSDK } = useContext(ExtensionContext)
  const [exploreUrl, setExploreUrl] = React.useState<any>('')
  const [exploreLoading, setExploreLoading] = React.useState<boolean>(false)
  const [query, setQuery] = React.useState<string>('')
  const [begin, setBegin] = React.useState<boolean>(false)
  const [submit, setSubmit] = React.useState<boolean>(false)
  const [db, setDb] = React.useState<boolean>(false)
  const [data, setData] = React.useState<any>({})
  const [exploreData, setExploreData] = React.useState<any>(null)

  /**
   * Initializes the application by performing the following steps:
   * 1. Initializes the database.
   * 2. Retrieves data from the 'chat history' store.
   * 3. Retrieves the fields of the specified LookML model explore.
   * 4. Extracts dimensions and measures from the fields.
   * 5. Sets the explore data with the extracted dimensions and measures.
   */
  const initialize = async () => {
    // const status = await initDB()
    // setDb(status)
    // const responses = await getStoreData('chat')
    const responses = await extensionSDK.localStorageGetItem('chat_history')
    setData(responses === null ? {} : JSON.parse(responses))
    const { fields } = await core40SDK.ok(
      core40SDK.lookml_model_explore(LOOKER_MODEL, LOOKER_EXPLORE, 'fields')
    )
    const dimensions = fields.dimensions.map((field: any) => {
      const { name, type, description } = field
      return (
        'name: ' +
        name +
        ', type: ' +
        type +
        ', description: ' +
        description +
        '\n'
      )
    })
    const measures = fields.measures.map((field: any) => {
      const { name, type, description } = field
      return (
        'name: ' +
        name +
        ', type: ' +
        type +
        ', description: ' +
        description +
        '\n'
      )
    })
    setExploreData({ dimensions: dimensions, measures: measures })
  }

  useEffect(() => {
    if (begin) {
      initialize()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [begin])

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    setQuery(e.currentTarget.value)
  }

  /**
   * Fetches data from the VERTEX_AI_ENDPOINT based on the provided prompt and fields.
   * If prompt is undefined, it uses the query as the prompt.
   * @param prompt - The prompt to be used for the question.
   * @param fields - The fields object containing dimensions and measures.
   * @returns {Promise<void>} - A promise that resolves when the data is fetched.
   */
  const fetchData = async (prompt: string | undefined, fields?: any): Promise<void> => {
    const question = prompt !== undefined ? prompt : query

    const responseData = await fetch(VERTEX_AI_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      
      body: JSON.stringify({
        explore: `Dimensions Used to group by information:\n 
        ${fields.dimensions.join(';')},\n 
        Measures are used to perform calculations (if top, bottom, total, sum, etc. are used include a measure):\n 
        ${fields.measures.join(';')}`,
        question: question,
        explore_label:LOOKER_EXPLORE
      }),
    })

    const exploreData = await responseData.text()
    console.log(exploreData)
    setExploreUrl(exploreData.trim() + '&toggle=dat,pik,vis')
    // await updateData('chat',question, { message: question, url: exploreData.trim() + '&toggle=dat,pik,vis'})
    data[question] = { message: question, url: exploreData.trim() + '&toggle=dat,pik,vis'}
    await extensionSDK.localStorageSetItem(`chat_history`,JSON.stringify(data))
  }

  /**
   * Handles the form submission.
   * 
   * @param prompt - The optional prompt string.
   */
  const handleSubmit = async (prompt: string | undefined) => {
    // const status = await initDB()
    // setDb(status)
    // await addData('chat', { message: query })
    // setData([...data, { message: prompt !== undefined ? prompt : query }])
    data[prompt !== undefined ? prompt : query] = { message: prompt !== undefined ? prompt : query}
    await extensionSDK.localStorageSetItem(`chat_history`,JSON.stringify(data))
    setData(data)
    setSubmit(true)
    fetchData(prompt, exploreData)
  }

  /**
   * Handles the submission of an example prompt.
   * @param {string} prompt - The prompt to submit.
   * @returns {Promise<void>} - A promise that resolves when the submission is complete.
   */
  const handleExampleSubmit = async (prompt: string) => {
    setQuery(prompt)
    handleSubmit(prompt)
    const elem = document.getElementById('historyScroll')
    if (elem) {
      elem.scrollTop = elem.scrollHeight
    }
  }

  /**
   * Handles the submission of a historical prompt. Doesn't issue a new network request
   * @param {string} prompt - The prompt to submit.
   * @returns {Promise<void>} - A promise that resolves when the submission is complete.
   */
  const handleHistorySubmit = async (prompt: string) => {
    const res = await extensionSDK.localStorageGetItem(`chat_history`) //getData('chat',prompt)
    setSubmit(true)
    setQuery(prompt)
    setExploreUrl(JSON.parse(res)[prompt].url)
  }

  const categorizedPrompts = [
    {
      category: 'Cohorting',
      prompt: 'Count of Users by first purchase date',
      color: 'blue',
    },
    {
      category: 'Audience Building',
      prompt:
        'Users who have purchased more than 100 dollars worth of Calvin Klein products and have purchased in the last 30 days',
      color: 'green',
    },
    {
      category: 'Period Comparison',
      prompt:
        'Total revenue by category this year compared to last year in a line chart with year pivoted',
      color: 'red',
    },
  ]

  const categorizedPromptsBilling = [
    {
      category: 'Billing Aggregate',
      prompt: 'Top billed services in the past 2 years.',
      color: 'blue'
    },
    {
      category: 'Time Series',
      prompt: 'Totaled Billed by month last year',
      color: 'green'
    }
  ]

  return (
    <Page height="100%" className={styles.root}>
      {!begin && <LandingPage begin={setBegin} />}
      {begin && (
        <SpaceVertical>
          <div
            className={styles.scrollbar}
            id={styles.layout}
          >
            <div
              className={styles.scrollbar}
              id={styles.subLayout}
            >
              <span className={styles.heading}>
                Explore Assistant Demo
              </span>
              <span className={styles.text}>
                Ask questions of a sample Ecommerce dataset powered by the Gemini model on Vertex AI.
              </span>
              <div
                style={{
                  width: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                  marginTop:'1.2rem'
                }}
              >
                <FieldTextArea
                  label="Type your prompt in here"
                  description="💡 Tip: Try asking for your data output in a viz!"
                  value={query}
                  onChange={handleChange}
                  onKeyDown={(e) => e.key === "Enter" && handleSubmit(undefined)}
                  description="Trained on an Ecommerce Dataset. Try asking for your data output in a viz!"
                  value={query}
                  onChange={handleChange}
                  width={'100%'}
                />
                <div
                  style={{
                    marginTop: '1rem',
                    marginBottom: '1rem',
                    display: 'flex',
                    flexDirection: 'row',
                    width: '100%',
                    height: '100%',
                    justifyContent: 'space-between',
                    alignContent: 'center',
                    alignItems: 'center',
                  }}
                >
                  <div style={{ width: 'auto' }}>
                    <button
                      disabled={submit}
                      onClick={() => handleSubmit(undefined)}
                      className={styles.customButton}
                      style={{ width: '100%', backgroundColor: 'rgb(26,115,232)', transition: 'background-color 0.2s cubic-bezier(0.3, 0, 0.5, 1)' }}
                    >
                      Run Prompt
                    </button>
                  </div>
                </div>
                <Tabs2 distributed>
                  <Tab2 id="examples" label="Sample Prompts">
                    <div
                      className={styles.scrollbar}
                      style={{ overflowY: 'scroll', height: '40vh', display:'flex',flexDirection:'column',justifyContent:'flex-start',alignItems:'center' }}
                    >
                      {(categorizedPrompts).map((item, index: number) => (
                        <div
                          key={index}
                          className={styles.card}
                          onClick={() => {
                            handleExampleSubmit(item.prompt)
                          }}
                        >
                          <span style={{ color: `${item.color}`}} className={styles.subHeading}>
                            {item.category}
                          </span>
                          <span className={styles.text} id="examplePrompt">
                            {item.prompt}
                          </span>
                        </div>
                      ))}
                    </div>
                  </Tab2>
                  <Tab2 id="history" label="Your History">
                    <div
                      className={styles.scrollbar}
                      id="historyScroll"
                      style={{ overflowY: 'scroll', height: '40vh', display:'flex',flexDirection:'column',justifyContent:'flex-start', alignItems:'center' }}
                    >
                      {
                      // db &&
                        Object.keys(data).length > 0 &&
                        Object.keys(data)
                          .filter((item: any) => data[item].message !== '')
                          .map((item: any, index: number) => {
                            return (
                              <div
                                key={index}
                                onClick={() => handleHistorySubmit(data[item].message)}
                                className={styles.card}
                              >
                                <span className={styles.text}>
                                  {data[item].message}
                                </span>
                              </div>
                            )
                          })}
                    </div>
                  </Tab2>
                </Tabs2>
              </div>
            </div>
            <div
              style={{
                height: '100vh',
                width: '100%',
                backgroundColor: '#f7f7f7',
                zIndex: 1,
              }}
            >
                <div
                  style={{
                    position:'relative',
                    backgroundColor: '#f7f7f7',
                    height: '100vh',
                    width: '100%',
                  }}
                >
                  <div style={{
                    width:'100%',
                    height:'100%',
                    display:'flex',
                    justifyContent:'center',
                    alignItems:'center',
                    position:'absolute',
                    zIndex:!exploreLoading ? 1 : -1
                  }}>
                    <BardLogo />
                  </div>
                  {exploreUrl && (
                    <ExploreEmbed
                      exploreUrl={exploreUrl}
                      setExploreLoading={setExploreLoading}
                      submit={submit}
                      setSubmit={setSubmit}
                    />
                  )}
                </div>
            </div>
          </div>
        </SpaceVertical>
      )}
    </Page>
  )
}

const LandingPage = ({ begin }: { begin: boolean }) => {
  const docs = [
    {
      title: 'No Code Prompt Tuning',
      model: 'Vertex AI Generative AI Studio',
      description:
        'No code prompt tuning of foundational model with generated Python code for engineer hand off.',
      doc: 'https://cloud.google.com/vertex-ai/docs/generative-ai/learn/generative-ai-studio',
    },
    {
      title: 'Generate Text',
      model: 'gemini-pro',
      description:
        'Multi-modal Model by Google. Used to generate the Explore query URL. This is done based off a minimal set of question answer examples that are fed into the prompt context.',
      doc: 'https://developers.generativeai.google/tutorials/text_quickstart',
    },
  ]

  return (
    <SpaceVertical>
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          alignItems: 'center',
          alignContent: 'center',
          width: '100%',
          height: '100%',
          padding: '2rem',
          paddingTop: '10rem',
          zIndex: 1,
        }}
      >
        <div
          style={{
            width: '40vw',
          }}
        >
          <span
           className={styles.title}
           >
            Explore Assistant Demo
          </span>
          <span className={styles.subTitle}>
            Powered by Generative AI with Google
          </span>
          <button className={styles.customButton} style={{ backgroundColor: 'rgb(26,115,232)' }} onClick={() => begin(true)}>Begin</button>
          {docs.map((doc, index) => {
            return (
              <a
                href={doc.doc}
                target="_blank"
                rel="noreferrer"
                key={index}
              >
                <div
                  style={{
                    cursor: 'pointer',
                    width: '90%',
                    height: '18vh',
                    backgroundColor: 'white',
                    marginTop: '2rem',
                    borderRadius: '5px',
                    display: 'flex',
                    flexDirection: 'row',
                  }}
                >
                  <div
                    style={{
                      width: '20%',
                      height: 'auto',
                      borderRight: '1px solid #ccc',
                    }}
                  >
                    <img
                      height="70%"
                      width="auto"
                      src={'https://lh3.googleusercontent.com/-1brN-k2sapOWO4gfdJKGEH8kZbfFjrzEMjNs1dl4u64PBH-yxVmB5vG2aHDatRudSByL3lwViUg1w'}
                    />
                  </div>
                  <div
                    style={{
                      paddingTop: '1rem',
                      paddingLeft: '1rem',
                      width: '80%',
                      height: 'auto',
                      display: 'flex',
                      flexDirection: 'column',
                    }}
                  >
                    <span className={styles.heading}>
                      {doc.title}
                    </span>
                    <span className={styles.subHeading}>
                      {doc.model}
                    </span>
                    <p
                      style={{
                        fontSize: '0.8rem',
                        width: 'auto',
                        height: 'auto',
                        color: 'black',
                        opacity: 0.8,
                      }}
                    >
                      {doc.description}
                    </p>
                  </div>
                </div>
              </a>
            )
          })}
        </div>
      </div>
    </SpaceVertical>
  )
}

export interface BardLogoProps {
  search?: boolean | undefined
}

const BardLogo = ({ search }: BardLogoProps) => {
  const SVG = () => (
    <svg width={'30%'} height={'30%'} viewBox="0 -900 900 900" >
      <path fill="url(#b)" className={styles.bard} d="M700-480q0-92-64-156t-156-64q92 0 156-64t64-156q0 92 64 156t156 64q-92 0-156 64t-64 156ZM80-80v-720q0-33 23.5-56.5T160-880h400v80H160v525l46-45h594v-241h80v241q0 33-23.5 56.5T800-240H240L80-80Zm160-320v-80h400v80H240Zm0-120v-80h360v80H240Zm0-120v-80h200v80H240Z"/>
      <linearGradient id='b' gradientUnits='objectBoundingBox' x1='0' y1='1' x2='1' y2='1'>
         <stop offset='0' stop-color='#1A73E8'>
            <animate attributeName="stop-color"
               values="blue;cyan;peach;yellow;orange;blue" dur="20s" repeatCount="indefinite">
            </animate>
         </stop>
         <stop offset='1' stop-color='#FFDDB7' stop-opacity="0">
            <animate attributeName="stop-color"
               values="peach;orange;red;purple;cyan;blue;green;peach" dur="20s" repeatCount="indefinite">
            </animate>
         </stop>
         <animateTransform attributeName="gradientTransform" type="rotate" values="360 .5 .5;0 .5 .5"
            dur="10s" repeatCount="indefinite" />
      </linearGradient>
    </svg>
  )
  return (
    <>
      {search ? (
        <div
          style={{
            zIndex: 1,
            height: '100%',
            width: '100%',
            display: 'flex',
            flexDirection: 'row',
          }}
        >
          <h3 style={{ color: 'rgb(26, 115, 232)' }}>Matching</h3>
          {SVG()}
        </div>
      ) : (
        <>{SVG()}</>
      )}
    </>
  )
}

export const App = hot(ExploreAssistant)
export { BardLogo }
