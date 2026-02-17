// For now, we will just render the Dashboard.
// Routing will be added later.
import Dashboard from './pages/Dashboard';
import Strategy from './pages/Strategy';
import AssetHistory from './pages/AssetHistory';

function App() {
  return (
    <>
      <header>
        <h1>Custom Seven Split</h1>
        <nav>
          {/* Basic navigation for now */}
          <a href="#" style={{padding: '0 10px'}}>Dashboard</a>
          <a href="#" style={{padding: '0 10px'}}>Strategy</a>
          <a href="#" style={{padding: '0 10px'}}>Asset History</a>
        </nav>
      </header>
      <main>
        <Dashboard />
        <Strategy />
        <AssetHistory />
      </main>
    </>
  );
}

export default App;
