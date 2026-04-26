const ORCHESTRATOR_BASE_URL =
  (import.meta.env.VITE_ORCHESTRATOR_URL as string | undefined)?.trim() ||
  'http://localhost:8080';

export interface PaperAnalysis {
  title: string;
  summary: string;
  keyFindings: string[];
  methodologyCritique: string;
  citationImpact: string;
  similarLiterature: string[];
  limitations: string[];
  confidenceScore?: number;
  rawResult?: FullReviewResponse;
}

interface MethodologyReport {
  identified_strengths?: string[];
  identified_weaknesses?: string[];
  recommendations?: string[];
  confidence_score?: number;
  reproducibility_assessment?: {
    overall_score?: number;
  };
  methodological_rigor?: {
    overall_score?: number;
  };
  error?: string;
}

interface FullReviewResponse {
  file_id: string;
  status: string;
  reports: {
    methodology?: MethodologyReport;
    summarizer?: {
      summary?: string;
      error?: string;
    };
    [key: string]: unknown;
  };
}

function toTitleCaseFromFilename(filename: string): string {
  return filename
    .replace(/\.pdf$/i, '')
    .replace(/[_-]+/g, ' ')
    .trim();
}

function mapFullReviewToPaperAnalysis(
  file: File,
  payload: FullReviewResponse,
): PaperAnalysis {
  const methodology = payload.reports?.methodology;
  const summarizer = payload.reports?.summarizer;
  const fallbackSummary = 'Analysis completed. Detailed agent insights are available in this report.';

  const reproducibility = methodology?.reproducibility_assessment?.overall_score;
  const rigor = methodology?.methodological_rigor?.overall_score;

  const citationImpact =
    typeof reproducibility === 'number' || typeof rigor === 'number'
      ? `Reproducibility ${reproducibility ?? 'N/A'} / 100, Methodological rigour ${rigor ?? 'N/A'} / 100.`
      : 'Citation impact assessment is pending the dedicated citation agent.';

  const methodologyCritique = methodology?.error
    ? `Methodology agent returned an error: ${methodology.error}`
    : methodology?.identified_weaknesses?.join('\n') ||
      'No major methodological issues were identified by the current agent run.';

  const summarizerSummary = summarizer?.error
    ? `Summarizer agent returned an error: ${summarizer.error}`
    : summarizer?.summary || '';

  return {
    title: toTitleCaseFromFilename(file.name),
    summary: summarizerSummary || fallbackSummary,
    keyFindings:
      methodology?.identified_strengths?.length
        ? methodology.identified_strengths
        : ['Extraction completed and agent workflow executed.'],
    methodologyCritique,
    citationImpact,
    similarLiterature: [],
    limitations:
      methodology?.identified_weaknesses?.length
        ? methodology.identified_weaknesses
        : ['Only methodology agent is currently connected in orchestrator.'],
    confidenceScore: methodology?.confidence_score,
    rawResult: payload,
  };
}

export async function analyzePaper(file: File): Promise<PaperAnalysis> {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`${ORCHESTRATOR_BASE_URL}/api/v1/full-review`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `Request failed with status ${response.status}`);
    }

    const payload = (await response.json()) as FullReviewResponse;
    return mapFullReviewToPaperAnalysis(file, payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    console.error('Pipeline Analysis Error:', error);

    return {
      title: toTitleCaseFromFilename(file.name),
      summary: 'Upload failed before full analysis could complete.',
      keyFindings: ['Unable to fetch orchestrator result.'],
      methodologyCritique: `Pipeline error: ${message}`,
      citationImpact: 'Not available.',
      similarLiterature: [],
      limitations: ['No backend result received.'],
    };
  }
}
