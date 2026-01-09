import React, { useState, useEffect } from 'react';
import Dashboard from './components/Dashboard';
import Login from './components/Login';
import { supabase } from './lib/supabase';
import { LogOut } from 'lucide-react';

function App() {
  const [session, setSession] = useState(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  return (
    <div className="min-h-screen bg-brand-dark text-white font-sans">
      <header className="border-b border-white/10 p-6 flex justify-between items-center bg-black/20 backdrop-blur">
        <h1 className="text-3xl font-bold text-orange-500">
          Crypto Paper Trader
        </h1>
        <div className="flex items-center gap-6">
          <div className="text-sm text-gray-400 hidden md:block">Simulação Ativa • v1.0</div>
          {session && (
            <button
              onClick={handleLogout}
              className="p-2 hover:bg-white/5 rounded-lg text-gray-400 hover:text-red-400 transition-colors flex items-center gap-2 text-sm font-bold"
            >
              <LogOut size={18} />
              <span className="hidden sm:inline">SAIR</span>
            </button>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-8 px-4">
        {!session ? <Login /> : <Dashboard />}
      </main>
    </div>
  );
}

export default App;
