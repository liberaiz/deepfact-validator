import { Composition } from "remotion";
import { MainComposition } from "./MainComposition";

export const FPS = 30;
export const DURATION_SECONDS = 60;
export const WIDTH = 1920;
export const HEIGHT = 1080;

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="MainComposition"
        component={MainComposition}
        durationInFrames={FPS * DURATION_SECONDS}
        fps={FPS}
        width={WIDTH}
        height={HEIGHT}
      />
    </>
  );
};
