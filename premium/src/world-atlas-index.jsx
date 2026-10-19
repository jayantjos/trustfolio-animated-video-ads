import React from "react";
import {Composition, registerRoot} from "remotion";
import {WorldAtlas} from "./WorldAtlas.jsx";

const Root=()=><Composition id="TrustFolioWorldAtlas" component={WorldAtlas}
  durationInFrames={144} fps={24} width={1080} height={1920}
  defaultProps={{slug:"washing-machines"}} />;
registerRoot(Root);
