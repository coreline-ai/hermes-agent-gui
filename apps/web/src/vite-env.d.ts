/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_FEATURE_3D?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
