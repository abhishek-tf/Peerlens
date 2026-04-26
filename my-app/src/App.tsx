/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import ThreeScene from './components/ThreeScene';
import UploadView from './components/UploadView';
import ReviewDashboard from './components/ReviewDashboard';
import type { PaperAnalysis } from './services/gemini';

export default function App() {
  const [analysis, setAnalysis] = useState<PaperAnalysis | null>(null);
  const [fileUrl, setFileUrl] = useState<string | null>(null);

  const handleAnalysisComplete = (result: PaperAnalysis, url: string) => {
    setAnalysis(result);
    setFileUrl(url);
  };

  return (
    <div className="relative w-full h-screen overflow-hidden font-sans">
      <ThreeScene />
      
      <AnimatePresence mode="wait">
        {!analysis ? (
          <motion.div
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 1.1, filter: 'blur(10px)' }}
            transition={{ duration: 0.8 }}
          >
            <UploadView onAnalysisComplete={handleAnalysisComplete} />
          </motion.div>
        ) : (
          <motion.div
            key="dashboard"
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.8, ease: "circOut" }}
            className="h-full"
          >
            <ReviewDashboard 
              analysis={analysis} 
              fileUrl={fileUrl}
              onReset={() => {
                setAnalysis(null);
                setFileUrl(null);
              }} 
            />
          </motion.div>
        )}
      </AnimatePresence>

      <footer className="fixed bottom-0 left-0 right-0 h-8 bg-[#0a0a0a]/80 backdrop-blur-sm border-t border-white/5 px-8 flex items-center justify-between z-20 pointer-events-none overflow-hidden">
        <div className="flex gap-6 text-[8px] uppercase tracking-[0.3em] font-bold text-white/20">
          <span>PeerLens Neural Interface</span>
          <span>Cloud Sync: Active</span>
        </div>
        <div className="flex gap-6 text-[8px] uppercase tracking-[0.3em] font-bold text-white/20">
          <span>LATENCY: 12ms</span>
          <span>AI_CORE: V4.1-STABLE</span>
        </div>
      </footer>
    </div>
  );
}
