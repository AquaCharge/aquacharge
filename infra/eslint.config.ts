import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["cdk.out", "tailwind.config.js", "*.config.js"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["bin/**/*.{ts,tsx,jsx,js}", "lib/**/*.{ts,tsx,jsx,js}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      "@typescript-eslint/no-unused-vars": "off",
      "@typescript-eslint/no-explicit-any": "off",
    },
  }
);
