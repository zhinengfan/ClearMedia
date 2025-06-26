import { useState } from 'react';
import reactLogo from './assets/react.svg';
import viteLogo from '/vite.svg';
import './App.css';
import { Button } from '@/components/ui/button';

function App() {
  const [count, setCount] = useState(0);

  return (
    <div className="min-h-screen bg-secondary-50 flex flex-col items-center justify-center">
      <div className="flex gap-4 mb-8">
        <a href="https://vite.dev" target="_blank">
          <img
            src={viteLogo}
            className="logo hover:opacity-80 transition-opacity"
            alt="Vite logo"
          />
        </a>
        <a href="https://react.dev" target="_blank">
          <img
            src={reactLogo}
            className="logo react hover:opacity-80 transition-opacity"
            alt="React logo"
          />
        </a>
      </div>
      <h1 className="text-4xl font-bold text-secondary-900 mb-8">
        Vite + React
      </h1>
      <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full mx-4">
        <Button
          onClick={() => setCount((count) => count + 1)}
          className="w-full mb-4"
        >
          count is {count}
        </Button>
        <p className="text-secondary-600 text-center">
          Edit{' '}
          <code className="bg-secondary-100 px-2 py-1 rounded text-secondary-800">
            src/App.tsx
          </code>{' '}
          and save to test HMR
        </p>
      </div>
      <p className="text-secondary-500 mt-6 text-center">
        Click on the Vite and React logos to learn more
      </p>
    </div>
  );
}

export default App;
