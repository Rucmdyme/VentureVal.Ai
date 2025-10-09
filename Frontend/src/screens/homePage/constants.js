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
    desc: "Drop your startup decks - we’ll extract key signals",
    formats: "Supports: .pdf,.txt,.jpg,.jpeg,.png",
    icon: "description",
  },
  {
    key: "call_transcript",
    title: "Call Transcripts",
    desc: "Drop call transcripts and meeting notes - we’ll summarize key insights with sentiment analysis",
    formats: "Supports: .pdf,.txt,.jpg,.jpeg,.png",
    icon: "call",
  },
  {
    key: "founder_update",
    title: "Founder Updates",
    desc: "Drop founder updates - we’ll track progress and growth signals",
    formats: "Supports: .pdf,.txt,.jpg,.jpeg,.png",
    icon: "trending_up",
  },
  {
    key: "email_communication",
    title: "Email Communications",
    desc: "Drop email communications - we’ll extract investor-relevant highlights",
    formats: "Supports: .pdf,.txt,.jpg,.jpeg,.png",
    icon: "mail_outline",
  },
];

export const whatYouWllGet = [
  {
    title: "Executive Summary",
    desc: "Clear overview of the startup’s strengths and challenges",
  },
  {
    title: "Market Analysis",
    desc: "Competitive landscape and sector positioning",
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
    desc: "Investor-ready notes formatted for IC review",
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

export const FAQS = [
  {
    question: "How does our AI-powered analysis benefit my startup?",
    answer:
      "Our AI delivers actionable insights from your documents, helping you prepare investor-ready pitches and strategies faster.",
  },
  {
    question: "What types of documents can I upload?",
    answer:
      "You can upload pitch decks, business plans, financial reports, or any strategic documents you’d like analyzed.",
  },
  {
    question: "How secure is my data?",
    answer:
      "Your data is encrypted and securely stored. We never share your documents with third parties.",
  },
  {
    question: "What pricing options are available?",
    answer:
      "We offer flexible plans for early-stage startups, scale-ups, and enterprises. Choose the plan that fits your growth stage.",
  },
  {
    question: "Can I integrate with my existing tools?",
    answer:
      "Yes! Our platform integrates with commonly used tools to make adoption seamless.",
  },
];

export const CONTACT_US_CONFIG = [
  {
    label: "Full Name",
    key: "name",
    required: true,
  },
  {
    label: "Email Address",
    key: "email",
    required: true,
  },
  {
    label: "Phone Number (optional)",
    key: "mobile",
  },
  {
    label: "Message",
    key: "message",
    required: true,
    multiline: true,
    rows: 4,
  },
];
