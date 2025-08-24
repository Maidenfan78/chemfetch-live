import { useConfirmStore } from '@/lib/store';
import React from 'react';
import { PanResponder, View, ViewStyle } from 'react-native';

interface CropOverlayProps {
  cropBoxStyle: ViewStyle;
}

export const CropOverlay = ({ cropBoxStyle }: CropOverlayProps) => {
  const setCrop = useConfirmStore(s => s.setCrop);

  const imageLayout = useConfirmStore.getState().photo
    ? {
        width: useConfirmStore.getState().photo.width,
        height: useConfirmStore.getState().photo.height,
      }
    : { width: 1, height: 1 };

  const makePanResponder = (type: 'top' | 'bottom' | 'left' | 'right' | 'box') =>
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onPanResponderMove: (_, g) => {
        const { dx, dy } = g;
        const w = imageLayout.width;
        const h = imageLayout.height;

        setCrop(prev => {
          let { leftRatio, topRatio } = prev;
          const { widthRatio, heightRatio } = prev;

          if (type === 'box') {
            leftRatio = Math.max(0, Math.min(leftRatio + dx / w, 1 - widthRatio));
            topRatio = Math.max(0, Math.min(topRatio + dy / h, 1 - heightRatio));
          } else if (type === 'top') {
            const top = topRatio + dy / h;
            const height = heightRatio - dy / h;
            return height > 0.05
              ? { ...prev, topRatio: Math.max(0, top), heightRatio: Math.min(1, height) }
              : prev;
          } else if (type === 'bottom') {
            const height = heightRatio + dy / h;
            return height > 0.05 ? { ...prev, heightRatio: Math.min(1 - topRatio, height) } : prev;
          } else if (type === 'left') {
            const left = leftRatio + dx / w;
            const width = widthRatio - dx / w;
            return width > 0.05
              ? { ...prev, leftRatio: Math.max(0, left), widthRatio: Math.min(1, width) }
              : prev;
          } else if (type === 'right') {
            const width = widthRatio + dx / w;
            return width > 0.05 ? { ...prev, widthRatio: Math.min(1 - leftRatio, width) } : prev;
          }

          return { ...prev, leftRatio, topRatio };
        });
      },
    });

  const panHandlers = {
    box: makePanResponder('box').panHandlers,
    top: makePanResponder('top').panHandlers,
    bottom: makePanResponder('bottom').panHandlers,
    left: makePanResponder('left').panHandlers,
    right: makePanResponder('right').panHandlers,
  };

  return (
    <View
      style={[
        cropBoxStyle,
        {
          position: 'absolute',
          borderWidth: 3,
          borderColor: '#4af',
          borderRadius: 10,
        },
      ]}
      {...panHandlers.box}
    >
      <View
        style={{
          position: 'absolute',
          top: '50%',
          left: 0,
          right: 0,
          height: 1,
          backgroundColor: '#4af',
        }}
        pointerEvents="none"
      />

      <View
        style={{
          position: 'absolute',
          top: -10,
          left: -20,
          right: -20,
          height: 20,
          backgroundColor: '#4af',
          opacity: 0.6,
        }}
        {...panHandlers.top}
      />
      <View
        style={{
          position: 'absolute',
          bottom: -10,
          left: -20,
          right: -20,
          height: 20,
          backgroundColor: '#4af',
          opacity: 0.6,
        }}
        {...panHandlers.bottom}
      />
      <View
        style={{
          position: 'absolute',
          top: -20,
          bottom: -20,
          left: -10,
          width: 20,
          backgroundColor: '#4af',
          opacity: 0.6,
        }}
        {...panHandlers.left}
      />
      <View
        style={{
          position: 'absolute',
          top: -20,
          bottom: -20,
          right: -10,
          width: 20,
          backgroundColor: '#4af',
          opacity: 0.6,
        }}
        {...panHandlers.right}
      />
    </View>
  );
};
