import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import cssInjectedByJsPlugin from "vite-plugin-css-injected-by-js"

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(), 
    cssInjectedByJsPlugin(), // Inject CSS into JS for Streamlit compatibility
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  base: "./",
  build: {
    outDir: "dist",
    assetsDir: "assets",
    cssCodeSplit: false, // Bundle all CSS into one file
    rollupOptions: {
      output: {
        manualChunks: undefined, // Ensure single JS bundle
      },
    },
  },
})