import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import react from "eslint-plugin-react";
import jsxA11y from "eslint-plugin-jsx-a11y";
import security from "eslint-plugin-security";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // Files to ignore
  {
    ignores: ["dist/**", "coverage/**", "node_modules/**", "*.config.js"],
  },

  // Base JavaScript rules
  js.configs.recommended,

  // Security rules (applies to all files)
  security.configs.recommended,

  // TypeScript + React rules for .ts/.tsx files
  {
    files: ["**/*.{ts,tsx}"],
    extends: [...tseslint.configs.strictTypeChecked, ...tseslint.configs.stylisticTypeChecked],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
      parserOptions: {
        project: ["./tsconfig.app.json"],
        tsconfigRootDir: import.meta.dirname,
      },
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      react,
      "jsx-a11y": jsxA11y,
    },
    rules: {
      // React Hooks
      ...reactHooks.configs.recommended.rules,

      // React Refresh (for Vite HMR)
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],

      // React (new JSX transform: no need to import React)
      "react/react-in-jsx-scope": "off",
      "react/prop-types": "off", // TypeScript handles this
      "react/display-name": "warn",

      // Accessibility
      ...jsxA11y.configs.recommended.rules,

      // TypeScript strict overrides
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/consistent-type-imports": ["error", { prefer: "type-imports" }],
      "@typescript-eslint/no-explicit-any": "error",
    },
    settings: {
      react: { version: "detect" },
    },
  },

  // Relax certain rules in test files
  {
    files: ["**/*.{test,spec}.{ts,tsx}", "src/test/**/*.{ts,tsx}"],
    rules: {
      "security/detect-object-injection": "off",
      "@typescript-eslint/no-explicit-any": "off",
      "@typescript-eslint/no-unsafe-assignment": "off",
    },
  },
);
