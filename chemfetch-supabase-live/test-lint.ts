// Simple test file to verify ESLint is working
export const testMessage = 'Hello from ChemFetch!';

export function greet(name: string): string {
  return `Hello, ${name}!`;
}

// This should trigger a console warning
console.log(testMessage);
