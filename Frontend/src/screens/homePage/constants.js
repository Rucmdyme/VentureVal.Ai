import {
  Description as FileText,
  Psychology as Brain,
  BarChart as BarChart3,
  Warning as AlertTriangle,
  CheckCircle,
} from "@mui/icons-material";

export const materialTypes = [
  {
    key: "pitch_deck",
    title: "Pitch Decks",
    desc: "Upload startup pitch presentations and decks",
    formats: "Supports: .pdf,.txt,.jpg,.jpeg,.png",
    icon: "description",
  },
  {
    key: "call_transcript",
    title: "Call Transcripts",
    desc: "Upload recorded call transcripts and meeting notes",
    formats: "Supports: .pdf,.txt,.jpg,.jpeg,.png",
    icon: "call",
  },
  {
    key: "founder_update",
    title: "Founder Updates",
    desc: "Upload investor updates and progress reports",
    formats: "Supports: .pdf,.txt,.jpg,.jpeg,.png",
    icon: "trending_up",
  },
  {
    key: "email_communication",
    title: "Email Communications",
    desc: "Upload email threads and correspondence",
    formats: "Supports: .pdf,.txt,.jpg,.jpeg,.png",
    icon: "mail_outline",
  },
];

export const whatYouWllGet = [
  {
    title: "Executive Summary",
    desc: "Key insights and strategic overview of the investment opportunity",
  },
  {
    title: "Market Analysis",
    desc: "Comprehensive market positioning and competitive landscape analysis",
  },
  {
    title: "Risk Assessment",
    desc: "Detailed risk evaluation and mitigation strategies",
  },
  {
    title: "Benchmarking",
    desc: "Performance metrics compared to industry standards",
  },
  {
    title: "Recommendations",
    desc: "Clear investment recommendations and next steps",
  },
  {
    title: "Structured Deal Notes",
    desc: "Professional format ready for investment committee review",
  },
];

export const processingSteps = [
  {
    id: "upload",
    label: "Processing Documents",
    description: "Analyzing uploaded files and extracting content",
    icon: FileText,
  },
  {
    id: "ai",
    label: "AI Analysis",
    description: "Running machine learning models on document content",
    icon: Brain,
  },
  {
    id: "metrics",
    label: "Extracting Key Metrics",
    description: "Identifying financial data and performance indicators",
    icon: BarChart3,
  },
  {
    id: "risks",
    label: "Generating Risk Analysis",
    description: "Evaluating potential risks and market factors",
    icon: AlertTriangle,
  },
  {
    id: "complete",
    label: "Finalizing Report",
    description: "Compiling comprehensive deal notes",
    icon: CheckCircle,
  },
];
