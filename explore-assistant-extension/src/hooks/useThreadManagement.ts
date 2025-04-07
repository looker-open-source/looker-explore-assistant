import { useCallback, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { 
  fetchUserThreads, 
  fetchThreadMessages, 
  setCurrentThread,
  newThreadState,
  resetChatNoNewThread,
  setIsChatMode,
  setSidePanelExploreUrl,
  openSidePanel
} from '../slices/assistantSlice';
import { RootState } from '../store';

const useThreadManagement = () => {
  const dispatch = useDispatch();
  const { 
    history, 
    currentExploreThread, 
    me,
    messageFetchStatus,
    isLoadingThreads
  } = useSelector((state: RootState) => state.assistant);
  const { isAuthenticated } = useSelector((state: RootState) => state.auth);

  // Load user threads on initial authentication
  useEffect(() => {
    if (isAuthenticated && me && history.length === 0) {
      return; // dispatch(fetchUserThreads());
    }
  }, [isAuthenticated, me, history.length, dispatch]);

  // Function to load a specific thread - matches the handleHistoryClick in Sidebar.tsx
  const loadThread = useCallback(async (thread) => {
    // First check if we need to fetch messages
    if (thread.messages.length === 0 && 
        (!messageFetchStatus[thread.uuid] || messageFetchStatus[thread.uuid] !== 'pending')) {
      dispatch(fetchThreadMessages(thread.uuid));
    }
    
    // Update the UI state to match existing Sidebar.tsx behavior
    dispatch(resetChatNoNewThread());
    dispatch(setCurrentThread(thread));
    dispatch(setIsChatMode(true));
    dispatch(setSidePanelExploreUrl(thread.exploreUrl));
    dispatch(openSidePanel());
    
    return thread;
  }, [messageFetchStatus, dispatch]);

  // Function to create a new thread - matches handleNewChat in Sidebar.tsx
  const createNewThread = useCallback(async () => {
    if (me) {
      const newThread = await dispatch(newThreadState(me)).unwrap();
      return newThread;
    }
    return null;
  }, [dispatch, me]);

  return {
    loadThread,
    createNewThread,
    threads: history,
    isLoadingThreads,
    isThreadMessagesLoading: (threadId) => messageFetchStatus[threadId] === 'pending'
  };
};

export default useThreadManagement;
