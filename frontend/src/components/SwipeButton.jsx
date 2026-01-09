import React, { useState } from "react";
import { motion, useMotionValue, useTransform } from "framer-motion";
import { Square, Play, Loader2 } from "lucide-react";

export const SwipeButton = ({ onSwipe, isRunning, isLoading }) => {
    const x = useMotionValue(0);
    const maxDrag = 220; // Width of trigger zone
    const threshold = 180; // Distance to trigger action
    const bgOpacity = useTransform(x, [0, maxDrag], [0.5, 1]);
    const [triggered, setTriggered] = useState(false);

    const handleDragEnd = () => {
        if (x.get() > threshold) {
            setTriggered(true);
            onSwipe();
            // Reset after a delay if loading fails or just to reset UI
            setTimeout(() => {
                setTriggered(false);
                x.set(0);
            }, 2000);
        } else {
            x.set(0);
        }
    };

    return (
        <div className="relative w-full h-14 rounded-xl overflow-hidden select-none touch-none">
            {/* Background Track */}
            <motion.div
                className={`absolute inset-0 flex items-center justify-center font-bold text-sm tracking-widest transition-colors duration-300
          ${isRunning
                        ? "bg-red-900/30 text-red-500 border border-red-500/20"
                        : "bg-emerald-900/30 text-emerald-500 border border-emerald-500/20"
                    }`}
                style={{ opacity: bgOpacity }}
            >
                <span>
                    {isLoading
                        ? "PROCESSANDO..."
                        : (isRunning ? "DESLIZE PARA PARAR >>>" : "DESLIZE PARA INICIAR >>>")}
                </span>
            </motion.div>

            {/* Draggable Handle */}
            <motion.div
                drag="x"
                dragConstraints={{ left: 0, right: maxDrag }}
                dragElastic={0.05}
                dragMomentum={false}
                onDragEnd={handleDragEnd}
                style={{ x }}
                className={`absolute left-1 top-1 bottom-1 w-12 rounded-lg cursor-grab active:cursor-grabbing flex items-center justify-center shadow-lg transition-colors z-10
          ${isRunning
                        ? "bg-gradient-to-r from-red-600 to-red-500 hover:from-red-500 hover:to-red-400 text-white shadow-red-900/40"
                        : "bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white shadow-emerald-900/40"
                    }`}
            >
                {isLoading ? (
                    <Loader2 size={20} className="animate-spin" />
                ) : isRunning ? (
                    <Square size={18} fill="currentColor" />
                ) : (
                    <Play size={18} fill="currentColor" />
                )}
            </motion.div>
        </div>
    );
};
