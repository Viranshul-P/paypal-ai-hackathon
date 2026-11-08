import { Route, Routes } from 'react-router-dom';

import Family from './pages/Family';
import Home from './pages/Home';
import Send from './pages/Send';
import Setup from './pages/Setup';

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/send" element={<Send />} />
      <Route path="/family" element={<Family />} />
      <Route path="/setup" element={<Setup />} />
      <Route path="*" element={<Home />} />
    </Routes>
  );
}
