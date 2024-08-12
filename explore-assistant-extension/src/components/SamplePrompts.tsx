import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { resetChat, setIsChatMode, setQuery } from '../slices/assistantSlice'
import { RootState } from '../store'

const SamplePrompts = () => {
  const dispatch = useDispatch()
  const {
    examples,
    exploreId,
  } = useSelector((state: RootState) => state.assistant)
  const [samplesLoaded, setSamplesLoaded] = React.useState(false)

  React.useEffect(() => {
    if(examples.exploreSamples.length > 0) {
      setSamplesLoaded(true)
      console.log(examples.exploreSamples)
    }
  },[examples.exploreSamples])

  const handleSubmit = (prompt: string) => {
    dispatch(resetChat())
    dispatch(setQuery(prompt))
    dispatch(setIsChatMode(true))
  }

  if(samplesLoaded) {
    const categorizedPrompts = JSON.parse(
      examples.exploreSamples.filter(
        explore => explore.explore_id === exploreId.replace("/",":")
      )
      ?.[0]
      ?.['samples'] ?? '[]'
    )

    return (
      <div className="flex flex-wrap max-w-5xl">
        {categorizedPrompts.map((item, index: number) => (
              <div
              className="flex flex-col w-56 bg-gray-200/50 hover:bg-gray-200 rounded-lg cursor-pointer text-sm p-4 m-2"
              key={index}
              onClick={() => {
                handleSubmit(item.prompt)
              }}
              >
                <div className="flex-grow font-light line-camp-5">{item.prompt}</div>
                <div className="mt-2 font-semibold justify-end">{item.category}</div>
              </div>
            ))
        }
      </div>
    )
  } else {
    return <></>
  }
}

export default SamplePrompts
