import React from 'react'
import {
  Box,
  Button,
  Card,
  Heading,
  Link,
  Paragraph,
  Space,
  SpaceVertical,
} from '@looker/components'
import { NavLink } from 'react-router-dom'

interface DocCardProps {
  title: string
  model: string
  description: string
  doc: string
}

const DocCard = ({ title, model, description, doc }: DocCardProps) => {
  return (
    <Link href={doc} target="_blank" rel="noreferrer">
      <Card p={'u2'} border={'none'}>
        <Space justify={'center'}>
          <Box borderRight={'ui2'}>
            <img
              height={'100px'}
              src={
                'https://lh3.googleusercontent.com/-1brN-k2sapOWO4gfdJKGEH8kZbfFjrzEMjNs1dl4u64PBH-yxVmB5vG2aHDatRudSByL3lwViUg1w'
              }
            />
          </Box>
          <SpaceVertical align={'start'} gap={'none'}>
            <Heading fontSize={'medium'} fontWeight={'bold'}>
              {title}
            </Heading>
            <Heading fontSize={'xsmall'} fontWeight={'semiBold'}>
              {model}
            </Heading>
            <Paragraph marginTop={'u4'} fontSize={'small'} color={'text2'}>
              {description}
            </Paragraph>
          </SpaceVertical>
        </Space>
      </Card>
    </Link>
  )
}

const LandingPage = () => {
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

  const logError = (error: Error, info: { componentStack: string }) => {
    // Do something with the error, e.g. log to an external API
    console.log("Error: ", error)
    console.log("Info: ", info)
  };

  return (
    <SpaceVertical>
      <SpaceVertical
        paddingTop={'10rem'}
        maxWidth={'30rem'}
        margin={'auto'}
        gap={'none'}
        >
        <Heading fontSize={'xxxxlarge'} fontWeight={'bold'}>
          Explore Assistant Demo
        </Heading>
        <Heading color={'inform'} fontSize={'large'} fontWeight={'semiBold'}>
          Powered by Generative AI with Google
        </Heading>
        <Space>
          <NavLink to="/assistant">
            <Button marginTop={'u8'}>Assistant</Button>
          </NavLink>
          <NavLink to="/chat">
            <Button marginTop={'u8'}>Chat</Button>
          </NavLink>
        </Space>

        <SpaceVertical marginTop={'u8'} gap={'u14'}>
          {docs.map((doc, index) => {
            return (
              <DocCard
                key={index}
                title={doc.title}
                model={doc.model}
                description={doc.description}
                doc={doc.doc}
                />
                )
              })}
        </SpaceVertical>
      </SpaceVertical>
    </SpaceVertical>
  )
}

export default LandingPage
