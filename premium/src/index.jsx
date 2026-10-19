import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {BubbleKingdom} from './Reel.jsx';

const Root=()=>{
  return <Composition id="TrustFolioBubbleKingdom" component={BubbleKingdom}
    durationInFrames={720} fps={24} width={1080} height={1920}/>;
};
registerRoot(Root);
