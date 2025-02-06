module.exports = {
    preset: 'ts-jest',
    testEnvironment: 'jsdom',
    setupFiles: ['dotenv/config', '<rootDir>/jest.setup.js'], // Add this line
    transform: {
      '^.+\\.ts?$': 'ts-jest',
      '^.+\\.md$': '<rootDir>/jest-raw-loader.js', // Add this line to use the custom transformer for .md files
    },
    transformIgnorePatterns: ['<rootDir>/node_modules/'],
  };