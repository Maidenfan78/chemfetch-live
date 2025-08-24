// lib/store.ts
import { create } from 'zustand';

interface CropRatios {
  leftRatio: number;
  topRatio: number;
  widthRatio: number;
  heightRatio: number;
}

interface ConfirmStore {
  photo: any | null;
  crop: CropRatios;
  setPhoto: (photo: any) => void;
  clearPhoto: () => void;
  setCrop: (crop: Partial<CropRatios> | ((prev: CropRatios) => Partial<CropRatios>)) => void;
  resetCrop: () => void;
}

const defaultCrop: CropRatios = {
  leftRatio: 0.1,
  topRatio: 0.4,
  widthRatio: 0.8,
  heightRatio: 0.2,
};

export const useConfirmStore = create<ConfirmStore>(set => ({
  photo: null,
  crop: { ...defaultCrop },
  setPhoto: photo => set({ photo }),
  clearPhoto: () => set({ photo: null }),
  setCrop: crop =>
    set(state => {
      const partial = typeof crop === 'function' ? crop(state.crop) : crop;

      return { crop: { ...state.crop, ...partial } };
    }),
  resetCrop: () => set({ crop: { ...defaultCrop } }),
}));

interface Product {
  barcode: string;
  name: string;
  size: string;
  sdsUrl?: string;
}

interface ProductState extends Product {
  setProduct: (p: Partial<Product>) => void;
  clear: () => void;
}

export const useProductStore = create<ProductState>(set => ({
  barcode: '',
  name: '',
  size: '',
  sdsUrl: '',
  setProduct: p => set(state => ({ ...state, ...p })),
  clear: () => set({ barcode: '', name: '', size: '', sdsUrl: '' }),
}));
