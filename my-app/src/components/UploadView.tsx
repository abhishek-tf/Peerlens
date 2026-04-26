import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Upload, ArrowRight } from 'lucide-react';
import { analyzePaper } from '../services/gemini';
import type { PaperAnalysis } from '../services/gemini';

interface UploadViewProps {
  onAnalysisComplete: (analysis: PaperAnalysis, url: string) => void;
}

export default function UploadView({ onAnalysisComplete }: UploadViewProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Only PDF files are supported.');
      return;
    }

    setError(null);
    setIsUploading(true);
    const url = URL.createObjectURL(file);

    try {
      const result = await analyzePaper(file);
      onAnalysisComplete(result, url);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Failed to process the file.';
      setError(message);
      URL.revokeObjectURL(url);
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  };

  return (
    <div className="relative z-10 flex flex-col items-center justify-center min-h-screen px-4 py-20 text-white">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-4xl text-center"
      >
        <span className="inline-block px-5 py-1.5 mb-8 text-[10px] font-bold tracking-[0.3em] uppercase border rounded-full border-gold/30 bg-gold/5 text-gold">
          PeerLens • Research Intelligence
        </span>
        <h1 className="mb-8 text-6xl font-serif italic tracking-tight md:text-8xl leading-none">
          Elegance in <br/>
          <span className="text-white/90">
            Scientific Review.
          </span>
        </h1>
        <p className="max-w-xl mx-auto mb-16 text-lg text-white/50 font-serif italic tracking-tight">
          Sophisticated neural analysis for the modern researcher. Upload your manuscript to visualize its global impact network.
        </p>

        <motion.div 
          className={`mt-10 p-12 border border-white/10 rounded-[2rem] transition-all max-w-2xl mx-auto ${
            dragActive ? 'border-gold bg-gold/5 scale-[1.02]' : 'bg-black/40 backdrop-blur-md'
          }`}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          whileHover={{ scale: 1.01 }}
        >
          <input 
            type="file" 
            className="hidden" 
            ref={fileInputRef} 
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />
          
          <AnimatePresence mode="wait">
            {isUploading ? (
              <motion.div 
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center"
              >
                <div className="w-12 h-12 mb-6 border-2 border-gold/30 border-t-gold rounded-full animate-spin" />
                <p className="text-gold font-mono text-[10px] tracking-[0.3em] uppercase">Deep Lens Scan...</p>
              </motion.div>
            ) : (
              <motion.div 
                key="upload"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="flex justify-center mb-8">
                  <div className="p-5 rounded-full border border-gold/20 bg-gold/5 text-gold">
                    <Upload className="w-8 h-8" />
                  </div>
                </div>
                <h3 className="mb-3 text-2xl font-serif italic">Lens Manuscript</h3>
                <p className="text-xs text-white/30 uppercase tracking-[0.2em] mb-8">Drop PDF or select to initiate</p>
                <div className="inline-flex items-center gap-3 px-6 py-3 border border-white/10 rounded-full text-white/60 hover:text-gold hover:border-gold/30 hover:bg-gold/5 transition-all text-sm font-medium tracking-wide group">
                  Begin Analysis <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
                </div>
                {error && <p className="mt-6 text-sm text-red-300">{error}</p>}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </div>
  );
}
