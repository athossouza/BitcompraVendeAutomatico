import React, { useState } from 'react';
import { supabase } from '../lib/supabase';
import { LogIn, ShieldAlert } from 'lucide-react';

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        const { error } = await supabase.auth.signInWithPassword({
            email,
            password,
        });
        if (error) setError(error.message);
        setLoading(false);
    };

    return (
        <div className="flex flex-col items-center justify-center min-h-[70vh]">
            <div className="bg-[#252525] p-8 rounded-3xl border border-white/5 shadow-2xl w-full max-w-md">
                <div className="flex flex-col items-center mb-8">
                    <div className="p-4 bg-orange-500/10 rounded-2xl mb-4 text-orange-500">
                        <LogIn size={48} />
                    </div>
                    <h2 className="text-2xl font-bold text-white">Área de Administração</h2>
                    <p className="text-gray-400 mt-2 text-center text-sm">Acesse com suas credenciais do Supabase para gerenciar o robô.</p>
                </div>

                <form onSubmit={handleLogin} className="space-y-4">
                    <div>
                        <label className="block text-xs font-bold text-gray-500 uppercase mb-2 ml-1">E-mail</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-orange-500 transition-all"
                            placeholder="seu@email.com"
                            required
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-bold text-gray-500 uppercase mb-2 ml-1">Senha</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full bg-black/30 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-orange-500 transition-all"
                            placeholder="••••••••"
                            required
                        />
                    </div>

                    {error && (
                        <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-xl flex items-center gap-2 text-sm text-center justify-center animate-shake">
                            <ShieldAlert size={18} />
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-gradient-to-r from-orange-600 to-orange-500 hover:from-orange-500 hover:to-orange-400 text-white font-bold py-4 rounded-xl shadow-lg shadow-orange-900/20 transition-all transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50"
                    >
                        {loading ? "VERIFICANDO..." : "ENTRAR NO SISTEMA"}
                    </button>
                </form>
            </div>
        </div>
    );
}
