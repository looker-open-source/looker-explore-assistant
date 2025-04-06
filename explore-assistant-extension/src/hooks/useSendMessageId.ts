import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';
import { ModelParameters } from './useSendVertexMessage';
import process from 'process';

// Add a mapping object to define the field name conversions
const messageFieldMapping = {
  // FE field name: BE field name
  // fields required to fully load a thread messages
  uuid: 'message_id',
  exploreUrl: 'explore_url',
  actor: 'actor',
  type: 'type',
  message: 'message',
  summarizedPrompt: 'summarized_prompt',
  summary: 'summary',
  createdAt: 'created_at',
  
    
  // other fields
  prompt_type: 'prompt_type',
  contents: 'contents',
  raw_prompt: 'raw_prompt',
  parameters: 'parameters',
  llm_response: 'llm_response',
  thread_id: 'thread_id',
  user_id: 'user_id'
};

// Add a helper function to convert FE field names to BE field names
const mapMessageFieldsToBE = (messageData: Record<string, any>): Record<string, any> => {
  const mappedData: Record<string, any> = {};
  
  // Loop through each key in the message data
  Object.entries(messageData).forEach(([feKey, value]) => {
    // Find the corresponding BE key from the mapping
    const beKey = messageFieldMapping[feKey as keyof typeof messageFieldMapping];
    
    if (beKey) {
      mappedData[beKey] = value;
    } else {
      // If no mapping exists, use the original key (fallback)
      mappedData[feKey] = value;
    }
  });
  
  return mappedData;
};

// For mapping back BE calls
const reverseMessageFieldMapping: Record<string, string> = {};
Object.entries(messageFieldMapping).forEach(([feKey, beKey]) => {
  reverseMessageFieldMapping[beKey] = feKey;
});

// Convert BE field names to FE field names
const mapMessageFieldsToFE = (messageData: Record<string, any>): Record<string, any> => {
    const mappedData: Record<string, any> = {};
    
    Object.entries(messageData).forEach(([beKey, value]) => {
      const feKey = reverseMessageFieldMapping[beKey];
      
      if (feKey) {
        mappedData[feKey] = value;
      } else {
        // If no mapping exists, use the original key (fallback)
        mappedData[beKey] = value;
      }
    });
    
    return mappedData;
  };
  


const useSendMessageId = () => {
    const { access_token } = useSelector((state: RootState) => state.auth);
    const {
        me,
        currentExploreThread,
        currentThreadID
    } = useSelector((state: RootState) => state.assistant as AssistantState);
    const VERTEX_AI_ENDPOINT = process.env.VERTEX_AI_ENDPOINT || '';

    const getMessageId = useCallback(
        async (
            contents: string,
            prompt_type: string,
            raw_prompt: string,
            parameters: ModelParameters,
            actor: string
        ) => {
            // Create message data with frontend field names
            const messageData = {
                user_id: me.id,
                thread_id: currentExploreThread.uuid,
                actor,
                contents,
                prompt_type,
                raw_prompt,
                parameters,
            };

            // Map to backend field names
            const mappedData = mapMessageFieldsToBE(messageData);

            try {
                const response = await fetch(`${VERTEX_AI_ENDPOINT}/message`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${access_token}`,
                    },
                    body: JSON.stringify(mappedData),
                });
            
                if (!response.ok || response.status !== 200) {
                    const error = await response.text();
                    throw new Error(`Server responded with ${response.status}: ${error}`);
                }
    
                const responseString = await response.json();
                return responseString.data.message_id;

            } catch (error) {
                console.error('Error in getMessageId:', error);
                throw error;
            }
        }, [currentExploreThread, access_token, me]);

    const updateMessage = useCallback(
        async (messageId: string, updateFields: { [key: string]: any }) => {
            // Create message data with frontend field names
            const messageData = {
                message_id: messageId,
                ...updateFields
            };

            // Map to backend field names
            const mappedData = mapMessageFieldsToBE(messageData);

            try {
                const response = await fetch(`${VERTEX_AI_ENDPOINT}/message/update`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${access_token}`,
                    },
                    body: JSON.stringify(mappedData),
                });
            
                if (!response.ok || response.status !== 200) {
                    const error = await response.text();
                    throw new Error(`Server responded with ${response.status}: ${error}`);
                }
    
                const responseString = await response.json();
                return responseString.data.message_id;

            } catch (error) {
                console.error('Error in updateMessage:', error);
                throw error;
            }
        },
        [access_token,currentExploreThread]
    )
    
    return { getMessageId, updateMessage };
};

export default useSendMessageId;