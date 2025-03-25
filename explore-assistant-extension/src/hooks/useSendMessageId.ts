import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';
import { ModelParameters } from './useSendVertexMessage';
import process from 'process';

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
            is_user: boolean
        ) => {

            const body = JSON.stringify({
                contents,
                prompt_type,
                current_explore_key: currentExploreThread.exploreKey,
                user_id: me.id,
                current_thread_id: currentExploreThread.uuid,
                raw_prompt,
                parameters,
                is_user
            })
            try {
                const response = await fetch(`${VERTEX_AI_ENDPOINT}/prompt`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${access_token}`,
                    },
                    body: body,
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

      
        }, [currentExploreThread, access_token]);

    const updateMessage = useCallback(
        async (messageId: string, updateFields: { [key: string]: any } ) => {
            const body = JSON.stringify({
                message_id: messageId,
                ...updateFields,
            })
            try {
                const response = await fetch(`${VERTEX_AI_ENDPOINT}/prompt/update`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${access_token}`,
                    },
                    body: body,
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