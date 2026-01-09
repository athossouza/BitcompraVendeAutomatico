import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { Activity, Play, Square, AlertOctagon, RefreshCw, TrendingUp, DollarSign, Wallet } from 'lucide-react';
import { motion } from 'framer-motion';
import { SwipeButton } from './SwipeButton';
import { PriceChart } from './PriceChart';

export default function Dashboard() {
    const [status, setStatus] = useState(null);
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        const interval = setInterval(fetchData, 2000);
        fetchData();
        return () => clearInterval(interval);
    }, []);

    const fetchData = async () => {
        try {
            const s = await api.getStatus();
            setStatus(s.data);
            const h = await api.getHistory();
            setHistory(h.data);
            setError(null);
        } catch (e) {
            console.error(e);
            setError("Conexão com o servidor perdida. Verifique se o backend está rodando.");
        }
    };

    const handleStart = async () => {
        setLoading(true);
        try { await api.startTrading(); fetchData(); } catch (e) { alert(e.response?.data?.detail || e.message); }
        setLoading(false);
    };

    const handleStop = async () => {
        setLoading(true);
        try { await api.stopTrading(); fetchData(); } catch (e) { console.error(e); }
        setLoading(false);
    };

    if (error && !status) return (
        <div className="flex flex-col items-center justify-center h-64 gap-4 animate-fade-in">
            <AlertOctagon size={48} className="text-red-500 animate-pulse" />
            <p className="text-gray-400 font-medium">{error}</p>
            <button onClick={fetchData} className="px-6 py-2 bg-orange-500/10 text-orange-500 rounded-xl hover:bg-orange-500/20 transition-all font-bold border border-orange-500/20">
                TENTAR NOVAMENTE
            </button>
        </div>
    );

    if (!status) return (
        <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500"></div>
        </div>
    );

    const formatTradeDate = (dateStr) => {
        const date = new Date(dateStr);
        const now = new Date();
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);

        const isToday = date.toDateString() === now.toDateString();
        const isYesterday = date.toDateString() === yesterday.toDateString();

        const timeStr = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        if (isToday) return `Hoje, ${timeStr}`;
        if (isYesterday) return `Ontem, ${timeStr}`;
        return `${date.toLocaleDateString('pt-BR')}, ${timeStr}`;
    };

    return (
        <div className="space-y-8 animate-fade-in-up">

            {/* FATAL ERROR ALERT */}
            {status && status.fatal_error && (
                <div className="bg-red-900/50 border border-red-500 text-red-100 p-6 rounded-2xl flex items-center gap-4 shadow-2xl animate-pulse">
                    <AlertOctagon size={32} className="text-red-500" />
                    <div>
                        <h3 className="text-xl font-bold">O Robô parou devido a erros críticos!</h3>
                        <p className="font-mono mt-1 text-sm opacity-80">{status.fatal_error}</p>
                    </div>
                </div>
            )}

            {/* Hero Stats */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {/* Card 1: Status Operacional */}
                <StatCard
                    label="Status Operacional"
                    value={status.running ? "ATIVO" : "PARADO"}
                    subValue={status.running ? "Motor de Trading Online" : "Aguardando Comando"}
                    color={status.running ? "text-emerald-400" : "text-gray-400"}
                    icon={status.running ? Activity : Square}
                    glow={status.running ? "shadow-emerald-500/20" : ""}
                />

                {/* Card 2: Preço Bitcoin */}
                <StatCard
                    label="Preço Bitcoin (Ao Vivo)"
                    value={status.current_price ? `R$ ${status.current_price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : "Carregando..."}
                    subValue="Global Market Ticker"
                    color="text-yellow-400"
                    icon={TrendingUp}
                    glow="shadow-yellow-500/20"
                    animateValue={true}
                />

                {/* Card 3: Patrimônio */}
                <StatCard
                    label="Patrimônio Total"
                    value={status.total_equity ? `R$ ${status.total_equity.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : `R$ ${status.balance.toFixed(2)}`}
                    subValue={status.total_equity ? `R$ ${status.balance.toLocaleString('pt-BR', { minimumFractionDigits: 0 })} (BRL) + R$ ${(status.total_equity - status.balance).toLocaleString('pt-BR', { minimumFractionDigits: 0 })} (BTC)` : "Capital Disponível"}
                    color="text-white"
                    icon={Wallet}
                    glow="shadow-orange-500/10"
                />

                {/* Card 4: Centro de Comando (Convertido para Card) */}
                <div className="relative bg-[#252525] p-6 rounded-2xl border border-white/5 shadow-xl overflow-hidden group">
                    {/* Background Icon */}
                    <div className="absolute top-0 right-0 p-4 opacity-10 text-gray-400">
                        <Play size={64} />
                    </div>
                    <div className="relative z-10 flex flex-col h-full justify-between">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 rounded-lg bg-white/5 text-blue-400">
                                <Play size={20} />
                            </div>
                            <span className="text-sm font-medium text-gray-400 uppercase tracking-wide">Centro de Comando</span>
                        </div>

                        <div className="mt-2">
                            <div className="mt-2 text-center">
                                <SwipeButton
                                    isRunning={status.running}
                                    isLoading={loading}
                                    onSwipe={status.running ? handleStop : handleStart}
                                />
                                <p className="text-xs text-gray-500 mt-2 font-mono opacity-60">
                                    {status.running ? "ARRASTE PARA DESATIVAR" : "ARRASTE PARA ATIVAR"}
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Card 5: Risco */}
                <StatCard
                    label="Proteção de Risco"
                    value={status.kill_switch ? "ACIONADA" : "ARMADA"}
                    subValue={status.kill_switch ? "Trading Desativado" : "Monitorando Perdas"}
                    color={status.kill_switch ? "text-red-500" : "text-blue-400"}
                    icon={AlertOctagon}
                    glow={status.kill_switch ? "shadow-red-500/20" : ""}
                />

                {/* Card 6: Carteira */}
                <StatCard
                    label="Carteira Cripto"
                    value={`${status.holdings.toFixed(6)} BTC`}
                    subValue="Posição Atual"
                    color="text-orange-400"
                    icon={Wallet}
                />
            </div>

            {/* Health Check Widget */}
            <div className="bg-[#1e1e1e] rounded-2xl border border-white/5 p-6 shadow-lg">
                <h3 className="text-white font-bold mb-4 flex items-center gap-2">
                    <Activity size={18} className="text-blue-400" />
                    Diagnóstico do Sistema
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <HealthItem
                        label="API de Mercado"
                        status={status.health?.market_api === "connected" ? "ok" : status.health?.market_api === "error" ? "error" : "warn"}
                        detail={status.health?.market_api === "connected" ? "Binance/MB" : "Sem Dados"}
                    />
                    <HealthItem
                        label="Engine de Trading"
                        status={status.running ? "ok" : "warn"}
                        detail={status.running ? "Rodando" : "Parado"}
                    />
                    <HealthItem
                        label="Banco de Dados"
                        status="ok"
                        detail={status.db_type || "Conectado"}
                    />
                    <HealthItem
                        label="Latência"
                        status={status.last_update && (Date.now() / 1000 - status.last_update) < 15 ? "ok" : "warn"}
                        detail={status.last_update ? `${(Date.now() / 1000 - status.last_update).toFixed(1)}s atrás` : "N/A"}
                    />
                </div>
            </div>

            {/* Trade Feed */}
            <div className="bg-[#1e1e1e] rounded-2xl border border-white/5 overflow-hidden shadow-2xl">
                <div className="p-6 border-b border-white/5 flex justify-between items-center bg-black/20">
                    <h2 className="text-xl font-bold flex items-center gap-3">
                        <RefreshCw size={20} className="text-orange-500" />
                        Feed de Execução
                    </h2>
                    <span className="text-xs font-mono text-gray-500 bg-white/5 px-2 py-1 rounded">TEMPO REAL</span>
                </div>
                <div className="overflow-x-auto max-h-[600px] scrollbar-thin scrollbar-thumb-gray-700">
                    <table className="w-full text-left">
                        <thead className="bg-white/5 text-gray-400 text-sm uppercase tracking-wider sticky top-0 backdrop-blur-md">
                            <tr>
                                <th className="p-4 font-medium">Operação</th>
                                <th className="p-4 font-medium">Preço (BRL)</th>
                                <th className="p-4 font-medium">Qtd (BTC)</th>
                                <th className="p-4 font-medium">Total</th>
                                <th className="p-4 font-medium">Data/Hora</th>
                                <th className="p-4 font-medium">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-white/5">
                            {history.slice().reverse().map((t, i) => (
                                <tr key={i} className="hover:bg-white/5 transition-colors group">
                                    <td className="p-4">
                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize
                      ${t.side === 'buy' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                                            {t.side === 'buy' ? 'COMPRA' : 'VENDA'}
                                        </span>
                                    </td>
                                    <td className="p-4 font-mono text-gray-300">R$ {t.filled_price.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}</td>
                                    <td className="p-4 font-mono text-gray-300">{t.quantity.toFixed(8)}</td>
                                    <td className="p-4 font-mono text-gray-400">R$ {(t.filled_price * t.quantity).toFixed(2)}</td>
                                    <td className="p-4 text-gray-500 text-sm whitespace-nowrap">{formatTradeDate(t.filled_at)}</td>
                                    <td className="p-4">
                                        <div className="flex items-center gap-2">
                                            <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                                            <span className="text-gray-400 text-sm capitalize">{t.status === 'filled' ? 'Executado' : t.status}</span>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {history.length === 0 && (
                                <tr>
                                    <td colSpan="6" className="p-12 text-center text-gray-500 italic">
                                        <div className="flex flex-col items-center gap-3">
                                            <TrendingUp size={48} className="opacity-20" />
                                            <span>Nenhum histórico de execução disponível</span>
                                        </div>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
            {/* Price Chart (Trade History) */}
            {history && history.length > 0 && (
                <div className="mb-6">
                    <PriceChart trades={history} />
                </div>
            )}

            {/* Status Logs */}
            {status.logs && status.logs.length > 0 && (
                <div className="bg-brand-card rounded-xl p-6 shadow-lg border border-red-500/20">
                    <h3 className="text-sm font-bold text-gray-400 uppercase mb-2">Logs do Sistema / Erros</h3>
                    <div className="space-y-1 font-mono text-xs max-h-96 overflow-y-auto custom-scrollbar">
                        {status.logs.map((log, i) => (
                            <div key={i} className={`${log.includes("ERROR") ? "text-red-400 font-bold" : "text-gray-500"}`}>
                                {log}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

function StatCard({ label, value, subValue, color = "text-white", icon: Icon, glow = "" }) {
    return (
        <motion.div
            whileHover={{ y: -5 }}
            className={`relative bg-[#252525] p-6 rounded-2xl border border-white/5 shadow-xl overflow-hidden group ${glow ? 'shadow-lg' : ''}`}
        >
            <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity ${color}`}>
                {Icon && <Icon size={64} />}
            </div>
            <div className="relative z-10">
                <div className="flex items-center gap-3 mb-2">
                    <div className={`p-2 rounded-lg bg-white/5 ${color}`}>
                        {Icon && <Icon size={20} />}
                    </div>
                    <span className="text-sm font-medium text-gray-400 uppercase tracking-wide">{label}</span>
                </div>
                <div className="mt-2">
                    <h3 className={`text-3xl font-bold tracking-tight ${color}`}>{value}</h3>
                    {subValue && <p className="text-xs text-gray-500 mt-1 font-medium">{subValue}</p>}
                </div>
            </div>
        </motion.div>
    );
}

function HealthItem({ label, status, detail }) {
    const colors = {
        ok: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
        warn: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
        error: "bg-red-500/10 text-red-400 border-red-500/20"
    };

    return (
        <div className={`p-3 rounded-xl border ${colors[status] || colors.warn} flex flex-col`}>
            <span className="text-xs text-gray-400 uppercase font-bold">{label}</span>
            <div className="flex items-center gap-2 mt-1">
                <div className={`w-2 h-2 rounded-full ${status === 'ok' ? 'bg-emerald-400' : status === 'error' ? 'bg-red-500' : 'bg-yellow-400'}`}></div>
                <span className="font-mono text-sm font-medium">{detail}</span>
            </div>
        </div>
    );
}
