import React, { useState, useMemo } from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
    ResponsiveContainer, ReferenceDot // Brush removed
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
        // Find main price data (could be trendline or price line)
        const pricePayload = payload.find(p => p.dataKey === 'price');
        const trade = pricePayload ? pricePayload.payload : payload[0].payload;

        return (
            <div className="bg-white p-3 rounded shadow-xl border border-gray-200 min-w-[160px]">
                <p className="text-gray-500 text-xs font-semibold mb-1 uppercase tracking-wider">
                    {new Date(trade.date).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short', year: 'numeric' })}
                    <span className="ml-1 opacity-50">{new Date(trade.date).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}</span>
                </p>
                <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${trade.side === 'buy' ? 'bg-blue-500' : 'bg-red-500'}`}></span>
                    <span className="text-gray-800 font-bold text-lg">
                        R$ {(trade.price / 1000).toFixed(2)}k
                    </span>
                </div>
                <div className={`mt-2 pt-2 border-t border-gray-100 text-xs font-bold uppercase ${trade.side === 'buy' ? 'text-blue-600' : 'text-red-600'}`}>
                    {trade.side === 'buy' ? '🔵 COMPRA' : '🔴 VENDA'}
                </div>
                <p className="text-xs text-gray-500 font-mono mt-0.5">
                    Qtd: {trade.quantity.toFixed(8)} BTC
                </p>
                <p className="text-xs text-gray-500 font-mono">
                    Total: R$ {trade.total.toFixed(2)}
                </p>
            </div>
        );
    }
    return null;
};

// --- Linear Regression Helper ---
const calculateTrendline = (data) => {
    if (!data || data.length < 2) return [];

    const n = data.length;
    let sumX = 0, sumY = 0, sumXY = 0, sumXX = 0;

    // Use index as X for simplicity, or timestamp
    data.forEach((point, i) => {
        const x = i;
        const y = point.price;
        sumX += x;
        sumY += y;
        sumXY += x * y;
        sumXX += x * x;
    });

    const slope = (n * sumXY - sumX * sumY) / (n * sumXX - sumX * sumX);
    const intercept = (sumY - slope * sumX) / n;

    return data.map((point, i) => ({
        date: point.date,
        trend: slope * i + intercept
    }));
};

// --- Custom Markers ---
const BuyMarker = (props) => {
    const { cx, cy, fill } = props;
    return (
        <svg x={cx - 6} y={cy - 6} width={12} height={12} viewBox="0 0 1024 1024" fill={fill}>
            {/* Up Triangle */}
            <path d="M512 0L128 768h768z" />
        </svg>
    );
};

const SellMarker = (props) => {
    const { cx, cy, fill } = props;
    return (
        <svg x={cx - 6} y={cy - 6} width={12} height={12} viewBox="0 0 1024 1024" fill={fill}>
            {/* Down Triangle */}
            <path d="M512 1024l384-768H128z" />
        </svg>
    );
};


export const PriceChart = ({ trades }) => {
    const [timeframe, setTimeframe] = useState('30d');

    const { data, trendlineData } = useMemo(() => {
        if (!trades || trades.length === 0) return { data: [], trendlineData: [] };

        const sortedTrades = [...trades].sort((a, b) => new Date(a.filled_at) - new Date(b.filled_at));

        const now = new Date();
        const cutoff = new Date();
        if (timeframe === '30d') cutoff.setDate(now.getDate() - 30);
        else if (timeframe === '60d') cutoff.setDate(now.getDate() - 60);
        else if (timeframe === 'all') cutoff.setFullYear(1900);

        const filtered = sortedTrades.filter(t => new Date(t.filled_at) >= cutoff);

        const mappedData = filtered.map(t => ({
            date: t.filled_at,
            price: t.filled_price,
            side: t.side,
            quantity: t.quantity,
            total: t.filled_price * t.quantity,
            color: t.side === 'buy' ? '#3b82f6' : '#ef4444'
        }));

        const trend = calculateTrendline(mappedData);

        // Merge trend into data for single chart data source if possible, 
        // OR just pass separate data to lines. Recharts likes unified data best usually.
        // Let's merge trend into mappedData
        const mergedData = mappedData.map((d, i) => ({
            ...d,
            trend: trend[i] ? trend[i].trend : null
        }));

        return { data: mergedData, trendlineData: trend };
    }, [trades, timeframe]);

    if (!data || data.length === 0) {
        return (
            <div className="h-[400px] flex items-center justify-center text-gray-500 text-sm font-mono border border-white/5 rounded-xl bg-[#1e1e1e]">
                <div className="text-center">
                    <p>Aguardando dados de operações...</p>
                    <p className="text-xs opacity-50 mt-1">Nenhum trade encontrado no período ({timeframe})</p>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full h-[450px] bg-[#1e1e1e] p-4 rounded-xl border border-white/5 shadow-lg flex flex-col">
            <div className="flex items-center justify-between mb-4 px-2">
                <div>
                    <h3 className="text-sm font-bold text-gray-200 uppercase tracking-wide">Histórico de Execuções</h3>
                    <p className="text-xs text-gray-500 font-mono hidden sm:block">Preço de Execução + Tendência Linear</p>
                </div>

                <div className="flex bg-black/20 rounded-lg p-1 border border-white/5">
                    {['30d', '60d', 'all'].map((tf) => (
                        <button
                            key={tf}
                            onClick={() => setTimeframe(tf)}
                            className={`px-3 py-1 text-xs font-bold rounded-md transition-all ${timeframe === tf
                                    ? 'bg-emerald-500/20 text-emerald-400 shadow-sm border border-emerald-500/20'
                                    : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                                }`}
                        >
                            {tf === 'all' ? 'TUDO' : tf.toUpperCase()}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex-1 w-full min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
                        <defs>
                            <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
                        <XAxis
                            dataKey="date"
                            stroke="#666"
                            tick={{ fontSize: 10 }}
                            tickMargin={10}
                            minTickGap={40}
                            tickFormatter={(str) => {
                                const d = new Date(str);
                                return `${d.getDate()}/${d.getMonth() + 1}`;
                            }}
                        />
                        <YAxis
                            domain={['auto', 'auto']}
                            stroke="#666"
                            tick={{ fontSize: 10 }}
                            tickFormatter={(value) => `R$${(value / 1000).toFixed(0)}k`}
                            width={50}
                        />
                        <Tooltip
                            content={<CustomTooltip />}
                            cursor={{ stroke: '#ffffff', strokeWidth: 1, strokeDasharray: '4 4' }}
                        />

                        {/* Trendline */}
                        <Line
                            type="monotone"
                            dataKey="trend"
                            stroke="#fbbf24" // Amber/Yellow for trend
                            strokeWidth={2}
                            strokeDasharray="5 5"
                            dot={false}
                            activeDot={false}
                            animationDuration={500}
                        />

                        {/* Price Line */}
                        <Line
                            type="monotone" // Smooth curve
                            dataKey="price"
                            stroke="#10b981"
                            strokeWidth={2}
                            dot={(props) => {
                                const { cx, cy, payload } = props;
                                if (payload.side === 'buy') return <BuyMarker cx={cx} cy={cy} fill="#3b82f6" />;
                                if (payload.side === 'sell') return <SellMarker cx={cx} cy={cy} fill="#ef4444" />;
                                return <circle cx={cx} cy={cy} r={4} fill="#10b981" />;
                            }}
                            activeDot={{ r: 8, stroke: '#fff', strokeWidth: 2 }}
                            animationDuration={800}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
