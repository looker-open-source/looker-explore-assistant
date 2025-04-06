import { useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { newThreadState, updateCurrentThreadWithSync } from '../slices/assistantSlice';
import { RootState } from '../store';

const useDropTempThread = () => {
  const dispatch = useDispatch();
  const { currentExploreThread, me } = useSelector((state: RootState) => state.assistant as newThreadState);

  const dropTempThread = useCallback(async () => {
    if (currentExploreThread?.uuid === 'temp') {
        const newThread = await dispatch(newThreadState(me)).unwrap();
        dispatch(
          updateCurrentThreadWithSync({
            uuid: newThread.uuid,
            exploreId: newThread.exploreId,
            modelName: newThread.modelName,
            exploreKey: newThread.exploreKey,
          })
        );
      }
  }, [currentExploreThread]);

  return dropTempThread;
};

export default useDropTempThread;
