import {Composition} from 'remotion';
import {BrandReel} from './BrandReel';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="BrandReel"
        component={BrandReel}
        durationInFrames={1450}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
