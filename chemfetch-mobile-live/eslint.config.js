// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require('eslint/config');
const expoConfig = require('eslint-config-expo/flat');

module.exports = defineConfig([
  expoConfig,
  {
    ignores: ['dist/*', 'node_modules/*', '.expo/*', 'build/*'],
    rules: {
      // React/JavaScript best practices
      'react/prop-types': 'off', // Using TypeScript
      'react/display-name': 'warn',
      'react/no-unescaped-entities': 'error',

      // General JavaScript best practices
      'no-console': 'off', // Allow console for debugging
      'no-debugger': 'error',
      'no-var': 'error',
      'prefer-const': 'error',
      eqeqeq: 'error',
      curly: 'error',

      // React Native best practices
      'no-unused-vars': 'off', // Handled by TypeScript
      'jsx-quotes': ['error', 'prefer-double'],
    },
  },
]);
