import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {BubbleKingdom} from './Reel.jsx';
import {WorldAtlas} from './WorldAtlas.jsx';

const Root=()=> <>
  <Composition id="TrustFolioBubbleKingdom" component={BubbleKingdom}
    durationInFrames={720} fps={24} width={1080} height={1920}/>
  <Composition id="TrustFolioWorldAtlas" component={WorldAtlas}
    durationInFrames={144} fps={24} width={1080} height={1920}
    defaultProps={{slug:"washing-machines"}}/>
</>;
registerRoot(Root);
