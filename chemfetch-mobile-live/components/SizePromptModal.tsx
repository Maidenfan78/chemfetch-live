import React from 'react';
import { Modal, Pressable, Text, TextInput, View } from 'react-native';

interface SizePromptModalProps {
  visible: boolean;
  name: string;
  size: string;
  onChangeSize: (value: string) => void;
  onSave: () => void;
  onCancel: () => void;
}

export const SizePromptModal = ({
  visible,
  name,
  size,
  onChangeSize,
  onSave,
  onCancel,
}: SizePromptModalProps) => {
  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onCancel}>
      <View className="flex-1 items-center justify-center bg-black/50">
        <View className="w-72 rounded-xl bg-white p-6">
          <Text className="mb-3 text-center text-base text-dark-100">
            Enter size/weight for <Text className="font-semibold">{name}</Text>
          </Text>
          <TextInput
            className="mb-4 rounded-md border border-gray-300 bg-light-100 px-3 py-2 text-dark-100"
            value={size}
            onChangeText={onChangeSize}
            placeholder="Size/weight"
            placeholderTextColor="#aaa"
          />
          <Pressable className="mb-2 rounded-lg bg-primary py-2" onPress={onSave}>
            <Text className="text-center font-bold text-white">Save</Text>
          </Pressable>
          <Pressable className="rounded-lg bg-gray-200 py-2" onPress={onCancel}>
            <Text className="text-center font-medium text-dark-100">Cancel</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
};
