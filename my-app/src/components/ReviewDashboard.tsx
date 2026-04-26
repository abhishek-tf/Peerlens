import React, { useState } from 'react';
import { motion } from 'motion/react';
import ReactMarkdown from 'react-markdown';
import {
  FileText,
  ExternalLink,
  PanelRightClose,
  PanelRightOpen,
} from 'lucide-react';
import type { PaperAnalysis } from '../services/gemini';

interface ReviewDashboardProps {
  analysis: PaperAnalysis;
  fileUrl: string | null;
  onReset: () => void;
}

export default function ReviewDashboard({ analysis, fileUrl, onReset }: ReviewDashboardProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const methodology = analysis.rawResult?.reports?.methodology;
  const reproducibility = methodology?.reproducibility_assessment;
  const rigor = methodology?.methodological_rigor;
  const strengths = methodology?.identified_strengths ?? [];
  const weaknesses = methodology?.identified_weaknesses ?? [];
  const recommendations = methodology?.recommendations ?? [];

  const methodologySections = [
    {
      title: 'Reproducibility',
      overall: reproducibility?.overall_score,
      items: [
        {
          label: 'Clarity',
          score: reproducibility?.clarity?.score,
          feedback: reproducibility?.clarity?.feedback,
          issues: reproducibility?.clarity?.issues,
          strengths: reproducibility?.clarity?.strengths,
        },
        {
          label: 'Completeness',
          score: reproducibility?.completeness?.score,
          feedback: reproducibility?.completeness?.feedback,
          issues: reproducibility?.completeness?.issues,
          strengths: reproducibility?.completeness?.strengths,
        },
        {
          label: 'Resource Availability',
          score: reproducibility?.resource_availability?.score,
          feedback: reproducibility?.resource_availability?.feedback,
          issues: reproducibility?.resource_availability?.issues,
          strengths: reproducibility?.resource_availability?.strengths,
        },
        {
          label: 'Replicability',
          score: reproducibility?.replicability?.score,
          feedback: reproducibility?.replicability?.feedback,
          issues: reproducibility?.replicability?.issues,
          strengths: reproducibility?.replicability?.strengths,
        },
      ],
    },
    {
      title: 'Methodological Rigor',
      overall: rigor?.overall_score,
      items: [
        {
          label: 'Study Design',
          score: rigor?.study_design?.score,
          feedback: rigor?.study_design?.feedback,
          issues: rigor?.study_design?.issues,
          strengths: rigor?.study_design?.strengths,
        },
        {
          label: 'Sample Adequacy',
          score: rigor?.sample_adequacy?.score,
          feedback: rigor?.sample_adequacy?.feedback,
          issues: rigor?.sample_adequacy?.issues,
          strengths: rigor?.sample_adequacy?.strengths,
        },
        {
          label: 'Evaluation Validity',
          score: rigor?.evaluation_validity?.score,
          feedback: rigor?.evaluation_validity?.feedback,
          issues: rigor?.evaluation_validity?.issues,
          strengths: rigor?.evaluation_validity?.strengths,
        },
        {
          label: 'Statistical Rigor',
          score: rigor?.statistical_rigor?.score,
          feedback: rigor?.statistical_rigor?.feedback,
          issues: rigor?.statistical_rigor?.issues,
          strengths: rigor?.statistical_rigor?.strengths,
        },
      ],
    },
  ];

  return (
    <div className="relative z-10 flex h-screen flex-col overflow-hidden text-[#e5e5e5] bg-[#080808]/40 backdrop-blur-3xl">
      <header className="h-16 shrink-0 border-b border-white/10 bg-[#0a0a0a]/70 backdrop-blur-md px-6 md:px-8 flex items-center gap-4">
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <div className="min-w-0">
            <div className="text-2xl md:text-3xl font-serif italic tracking-[0.08em] text-gold leading-none">
              PeerLens
            </div>
          </div>
        </div>

        <div className="hidden md:flex items-center justify-center min-w-0 flex-[2] px-4">
          <div className="text-[10px] uppercase tracking-[0.25em] text-white/40 truncate">
            Project: {analysis.title}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={onReset}
            className="px-4 py-1.5 border border-white/10 rounded-full text-[10px] uppercase tracking-widest hover:bg-white/5 hover:border-gold/30 hover:text-gold transition-all"
          >
            New
          </button>

          {!isSidebarOpen ? (
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 text-white/40 hover:text-gold transition-colors"
              title="Expand Analysis"
            >
              <PanelRightOpen className="w-5 h-5" />
            </button>
          ) : (
            <button
              onClick={() => setIsSidebarOpen(false)}
              className="p-2 text-white/20 hover:text-gold transition-colors"
              title="Collapse Analysis"
            >
              <PanelRightClose className="w-5 h-5" />
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 min-h-0 flex overflow-hidden">
        <div className="flex-1 border-r border-white/10 bg-black/20 flex flex-col relative min-w-0">
          <div className="flex-1 bg-[#111] relative overflow-hidden">
            {fileUrl ? (
              <object data={fileUrl} type="application/pdf" className="w-full h-full">
                <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center space-y-4 bg-black">
                  <FileText className="w-12 h-12 text-white/10" />
                  <p className="text-sm text-white/40 uppercase tracking-widest">
                    Unable to render PDF directly
                  </p>
                  <a
                    href={fileUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-gold/10 text-gold border border-gold/30 rounded-full hover:bg-gold/20 transition-all text-xs font-bold uppercase tracking-widest"
                  >
                    Open Manuscript Link <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              </object>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-white/10 space-y-4">
                <div className="w-8 h-8 border-2 border-white/5 border-t-gold rounded-full animate-spin" />
                <div className="text-[10px] uppercase tracking-[0.3em]">Preparing Manuscript...</div>
              </div>
            )}
          </div>
        </div>

        <motion.div
          initial={false}
          animate={{
            width: isSidebarOpen ? 'clamp(600px, 45vw, 800px)' : '0px',
            opacity: isSidebarOpen ? 1 : 0,
          }}
          transition={{ type: 'spring', damping: 20, stiffness: 100 }}
          className="overflow-hidden flex flex-col bg-[#0a0a0a]/95 backdrop-blur-3xl shadow-[-20px_0_40px_rgba(0,0,0,0.5)] z-20"
        >
          <div className="flex-1 overflow-y-auto custom-scrollbar p-10">
            <div className="max-w-2xl mx-auto space-y-16">
              <section>
                <h3 className="text-[10px] uppercase tracking-[0.4em] text-white/30 mb-6 font-bold">
                  Executive Summary
                </h3>
                <div className="text-xl font-serif italic leading-relaxed text-white/80 markdown-body">
                  <ReactMarkdown>{analysis.summary}</ReactMarkdown>
                </div>
              </section>

              <section className="space-y-12 border-t border-white/10 pt-16">
                <div>
                  <h3 className="text-[10px] uppercase tracking-[0.4em] text-white/30 mb-6 font-bold">
                    Methodology Review
                  </h3>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                    <MetricCard
                      label="Reproducibility"
                      value={
                        typeof reproducibility?.overall_score === 'number'
                          ? `${Math.round(reproducibility.overall_score * 10)}/100`
                          : 'N/A'
                      }
                    />
                    <MetricCard
                      label="Methodological Rigor"
                      value={
                        typeof rigor?.overall_score === 'number'
                          ? `${Math.round(rigor.overall_score * 10)}/100`
                          : 'N/A'
                      }
                    />
                    <MetricCard
                      label="Confidence"
                      value={
                        typeof analysis.confidenceScore === 'number'
                          ? `${Math.round(analysis.confidenceScore * 100)}%`
                          : 'N/A'
                      }
                    />
                  </div>
                </div>

                {methodologySections.map((section) => (
                  <div key={section.title} className="space-y-6">
                    <div className="flex items-end justify-between gap-4">
                      <h4 className="text-[10px] uppercase tracking-[0.4em] text-white/20 font-bold">
                        {section.title}
                      </h4>
                      {typeof section.overall === 'number' && (
                        <div className="text-[10px] uppercase tracking-[0.25em] text-gold/80">
                          Overall {Math.round(section.overall * 10)}/100
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-1 gap-4">
                      {section.items.map((item) => (
                        <div key={item.label} className="p-5 bg-white/5 border border-white/10 rounded-2xl space-y-4">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <div className="text-sm uppercase tracking-[0.2em] text-white/80">
                                {item.label}
                              </div>
                              {typeof item.score === 'number' && (
                                <div className="mt-2 h-1.5 w-40 max-w-full rounded-full bg-white/10 overflow-hidden">
                                  <div
                                    className="h-full bg-gold"
                                    style={{ width: `${Math.max(0, Math.min(100, item.score * 10))}%` }}
                                  />
                                </div>
                              )}
                            </div>

                            {typeof item.score === 'number' && (
                              <div className="text-xl font-serif italic text-gold/90">
                                {Math.round(item.score * 10)}/100
                              </div>
                            )}
                          </div>

                          {item.feedback && (
                            <p className="text-sm leading-relaxed text-white/70">
                              {item.feedback}
                            </p>
                          )}

                          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                            {item.strengths?.length ? (
                              <DetailList title="Strengths" items={item.strengths} tone="positive" />
                            ) : null}
                            {item.issues?.length ? (
                              <DetailList title="Issues" items={item.issues} tone="warning" />
                            ) : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}

                {strengths.length > 0 && (
                  <DetailList title="Overall Strengths" items={strengths} tone="positive" compact />
                )}

                {weaknesses.length > 0 && (
                  <DetailList title="Overall Weaknesses" items={weaknesses} tone="warning" compact />
                )}

                {recommendations.length > 0 && (
                  <DetailList title="Recommendations" items={recommendations} tone="neutral" compact />
                )}
              </section>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-4 bg-white/5 border border-white/5 rounded-xl text-center">
      <div className="text-[8px] uppercase tracking-widest text-white/30 mb-2">{label}</div>
      <div className="text-xl font-serif italic text-white/90">{value}</div>
    </div>
  );
}

function DetailList({
  title,
  items,
  tone,
  compact = false,
}: {
  title: string;
  items: string[];
  tone: 'positive' | 'warning' | 'neutral';
  compact?: boolean;
}) {
  const toneClasses =
    tone === 'positive'
      ? 'border-gold/20 bg-gold/5 text-gold/90'
      : tone === 'warning'
        ? 'border-red-400/20 bg-red-400/5 text-red-100'
        : 'border-white/10 bg-white/5 text-white/80';

  return (
    <div className={`rounded-2xl border p-4 ${toneClasses}`}>
      <div className="text-[10px] uppercase tracking-[0.25em] mb-3 font-bold opacity-70">
        {title}
      </div>
      <div className={compact ? 'space-y-2' : 'space-y-3'}>
        {items.map((item, index) => (
          <div key={`${title}-${index}`} className="text-sm leading-relaxed">
            {item}
          </div>
        ))}
      </div>
    </div>
  );
}

