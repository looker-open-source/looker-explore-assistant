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
    console.log('Question: ', prompt, query)
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
    console.log(data)
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
              <span
                style={{
                  fontSize: '2rem',
                  fontWeight: 'bold',
                  fontFamily: 'sans-serif',
                  letterSpacing: '-0.1rem',
                  lineHeight: '2.5rem',
                  marginBottom: '1rem',
                  display: 'block',
                  textAlign: 'left',
                  width: 'auto',
                  height: 'auto',
                  border: 'none',
                }}
              >
                Explore Assistant Demo
              </span>
              <h3 style={{ color: 'rgb(26, 115, 232)' }}>
                Powered by Generative AI with Google
              </h3>
              <div
                style={{
                  width: '100%',
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                <FieldTextArea
                  label="Type your prompt in here"
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
                    <Button
                      disabled={submit}
                      onClick={() => handleSubmit(undefined)}
                      style={{ width: '100%' }}
                    >
                      {submit ? <BardLogo search={true} /> : 'Run Prompt'}
                    </Button>
                  </div>
                </div>
                <Tabs2 distributed>
                  <Tab2 id="examples" label="Example Prompts">
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
                          <span
                            style={{
                              color: `${item.color}`,
                              fontSize: '1.3vh',
                            }}
                          >
                            {item.category}
                          </span>
                          <span style={{ fontSize: '2vh' }} id="examplePrompt">
                            {item.prompt}
                          </span>
                        </div>
                      ))}
                    </div>
                  </Tab2>
                  <Tab2 id="history" label="History">
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
                                <span style={{ fontSize: '1.5vh' }}>
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
              {!exploreLoading && <BardLogo />}
              {exploreUrl && (
                <div
                  style={{
                    position:'relative',
                    backgroundColor: '#f7f7f7',
                    height: '100vh',
                    width: '100%',
                  }}
                >
                  {exploreUrl && (
                    <ExploreEmbed
                      exploreUrl={exploreUrl}
                      setExploreLoading={setExploreLoading}
                      submit={submit}
                      setSubmit={setSubmit}
                    />
                  )}
                </div>
              )}
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
      model: 'text-bison-001',
      description:
        'Generative Text Model by Google. Used to Generate explore expanded url parameters. This is done based off 20 examples of question answer that is fed into the prompt context.',
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
            style={{
              fontSize: '4rem',
              fontWeight: 'bold',
              fontFamily: 'sans-serif',
              letterSpacing: '-0.1rem',
              lineHeight: '4.5rem',
              marginBottom: '1rem',
              display: 'block',
              textAlign: 'left',
              width: '100%',
              border: 'none',
            }}
          >
            Explore Assistant Demo
          </span>
          <h3 style={{ color: 'rgb(26, 115, 232)' }}>
            Powered by Generative AI with Google
          </h3>
          <Button onClick={() => begin(true)}>Begin</Button>
          {docs.map((doc, index) => {
            return (
              <a
                href={doc.doc}
                style={{ textDecoration: 'none' }}
                target="_blank"
                rel="noreferrer"
                key={index}
              >
                <div
                  style={{
                    cursor: 'pointer',
                    width: '100%',
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
                      width="70%"
                      src={
                        index === 0
                          ? 'https://lh3.googleusercontent.com/-1brN-k2sapOWO4gfdJKGEH8kZbfFjrzEMjNs1dl4u64PBH-yxVmB5vG2aHDatRudSByL3lwViUg1w'
                          : 'https://developers.generativeai.google/static/site-assets/images/marketing/home/icon-palm.webp'
                      }
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
                    <span
                      style={{
                        height: 'auto',
                        fontSize: '1.5rem',
                        fontWeight: 'bold',
                        fontFamily: 'sans-serif',
                        letterSpacing: '-0.1rem',
                        display: 'block',
                        textAlign: 'left',
                        width: '100%',
                        color: 'black',
                        border: 'none',
                      }}
                    >
                      {doc.title}
                    </span>
                    <p
                      style={{ color: 'rgb(26, 115, 232)', fontSize: '0.8rem' }}
                    >
                      {doc.model}
                    </p>
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
    <svg
      width="100%"
      height="100%"
      viewBox={search ? '-600 -300 9000 2500' : '0 -800 700 3000'}
      fill="none"
    >
      <path
        className={styles.bard}
        d="M515.09 725.824L472.006 824.503C455.444 862.434 402.954 862.434 386.393 824.503L343.308 725.824C304.966 638.006 235.953 568.104 149.868 529.892L31.2779 477.251C-6.42601 460.515 -6.42594 405.665 31.2779 388.929L146.164 337.932C234.463 298.737 304.714 226.244 342.401 135.431L386.044 30.2693C402.239 -8.75637 456.159 -8.75646 472.355 30.2692L515.998 135.432C553.685 226.244 623.935 298.737 712.234 337.932L827.121 388.929C864.825 405.665 864.825 460.515 827.121 477.251L708.53 529.892C622.446 568.104 553.433 638.006 515.09 725.824Z"
        fill="url(#paint0_radial_2525_777)"
      />
      <path
        d="M915.485 1036.98L903.367 1064.75C894.499 1085.08 866.349 1085.08 857.481 1064.75L845.364 1036.98C823.765 987.465 784.862 948.042 736.318 926.475L698.987 909.889C678.802 900.921 678.802 871.578 698.987 862.61L734.231 846.951C784.023 824.829 823.623 783.947 844.851 732.75L857.294 702.741C865.966 681.826 894.882 681.826 903.554 702.741L915.997 732.75C937.225 783.947 976.826 824.829 1026.62 846.951L1061.86 862.61C1082.05 871.578 1082.05 900.921 1061.86 909.889L1024.53 926.475C975.987 948.042 937.083 987.465 915.485 1036.98Z"
        fill="url(#paint1_radial_2525_777)"
      />
      <defs>
        <radialGradient
          id="paint0_radial_2525_777"
          cx="0"
          cy="0"
          r="1"
          gradientUnits="userSpaceOnUse"
          gradientTransform="translate(670.447 474.006) rotate(78.858) scale(665.5 665.824)"
        >
          <stop stopColor="#1BA1E3" />
          <stop offset="0.0001" stopColor="#1BA1E3" />
          <stop offset="0.300221" stopColor="#5489D6" />
          <stop offset="0.545524" stopColor="#9B72CB" />
          <stop offset="0.825372" stopColor="#D96570" />
          <stop offset="1" stopColor="#F49C46" />
          <animate
            attributeName="r"
            dur="5000ms"
            from="0"
            to="1"
            repeatCount="indefinite"
          />
        </radialGradient>
        <radialGradient
          id="paint1_radial_2525_777"
          cx="0"
          cy="0"
          r="1"
          gradientUnits="userSpaceOnUse"
          gradientTransform="translate(670.447 474.006) rotate(78.858) scale(665.5 665.824)"
        >
          <stop stopColor="#1BA1E3" />
          <stop offset="0.0001" stopColor="#1BA1E3" />
          <stop offset="0.300221" stopColor="#5489D6" />
          <stop offset="0.545524" stopColor="#9B72CB" />
          <stop offset="0.825372" stopColor="#D96570" />
          <stop offset="1" stopColor="#F49C46" />
          <animate
            attributeName="r"
            dur="5000ms"
            from="0"
            to="1"
            repeatCount="indefinite"
          />
        </radialGradient>
      </defs>
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
