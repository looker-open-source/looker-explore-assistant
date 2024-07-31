import React from 'react'
import { useDispatch } from 'react-redux'
import { resetChat, setIsChatMode, setQuery } from '../slices/assistantSlice'

const SamplePrompts = () => {
  const dispatch = useDispatch()
  const categorizedPrompts = [
    {
      category: 'Cohorting',
      prompt: 'Count of Users by first purchase date',
    },
    {
      category: 'Audience Building',
      prompt:
        'Users who have purchased more than 100 dollars worth of Calvin Klein products and have purchased in the last 30 days',
    },
    {
      category: 'Period Comparison',
      prompt:
        'Total revenue by category this year compared to last year in a line chart with year pivoted',
    },
  ]

  const handleSubmit = (prompt: string) => {
    dispatch(resetChat())
    dispatch(setQuery(prompt))
    dispatch(setIsChatMode(true))
  }
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
      ))}
    </div>
  )
}

export default SamplePrompts
