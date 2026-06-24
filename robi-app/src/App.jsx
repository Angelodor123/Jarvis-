import React, { useEffect } from 'react';
import useProfileStore from './store/profileStore.js';
import useGameStore from './store/gameStore.js';

import ProfileSelector  from './screens/ProfileSelector.jsx';
import ForestPath       from './screens/ForestPath.jsx';
import StopNarration    from './screens/StopNarration.jsx';
import GameRouter       from './screens/GameRouter.jsx';
import RoundComplete    from './screens/RoundComplete.jsx';
import ParentDashboard  from './screens/ParentDashboard.jsx';

export default function App() {
  const hydrate  = useProfileStore(s => s.hydrate);
  const hydrated = useProfileStore(s => s.hydrated);
  const screen   = useGameStore(s => s.screen);

  useEffect(() => { hydrate(); }, []);

  if (!hydrated) return null;

  return (
    <>
      {screen === 'profile'  && <ProfileSelector />}
      {screen === 'home'     && <ForestPath />}
      {screen === 'narration'&& <StopNarration />}
      {screen === 'game'     && <GameRouter />}
      {screen === 'complete' && <RoundComplete />}
      {screen === 'parent'   && <ParentDashboard />}
    </>
  );
}
