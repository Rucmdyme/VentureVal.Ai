# AI Startup Analyst

An intelligent investment analysis platform that leverages AI to evaluate startup opportunities and provide comprehensive risk assessments for venture capital decision-making.

## 🚀 Overview

AI Startup Analyst is a full-stack application that combines advanced AI analysis with interactive chat capabilities to help investors make data-driven decisions about startup investments. The platform analyzes company documents, financial data, and market information to generate detailed investment recommendations.

## ✨ Key Features

- **Comprehensive Startup Analysis**: Automated evaluation of financial metrics, market position, team assessment, and risk analysis
- **AI-Powered Chat Agent**: Interactive Q&A with contextual investment insights and follow-up suggestions
- **Risk Assessment Engine**: Multi-dimensional risk scoring with detailed mitigation strategies
- **Benchmark Comparison**: Performance analysis against industry standards and peer companies
- **Document Processing**: Intelligent extraction and analysis of startup documents and pitch decks
- **Investment Scoring**: Weighted scoring system with tier-based recommendations (PURSUE/CONSIDER/PASS)
- **Real-time Analytics**: Interactive dashboards with financial projections and market insights

## 🏗️ Architecture

### Backend (Python/FastAPI)
- **FastAPI** framework with async support
- **Google Gemini AI** integration for analysis and chat
- **Firebase Firestore** for data persistence
- **Modular router architecture** (analysis, documents, agent)
- **Enhanced text processing** and data sanitization
- **Usage monitoring** and cost tracking

### Frontend (React/Vite)
- **React 19** with modern hooks
- **Material-UI** components for professional interface
- **Recharts** for data visualization
- **Firebase hosting** for deployment
- **Responsive design** with mobile support

## 🛠️ Tech Stack

**Backend:**
- FastAPI 0.110.0+
- Google Gemini AI (genai 1.38.0)
- Firebase Admin SDK
- Python 3.8+

**Frontend:**
- React 19.1.1
- Material-UI 7.3.2
- Vite 7.1.2
- Axios for API communication
- React Router for navigation

**Infrastructure:**
- Google Cloud Platform
- Firebase Hosting
- Docker containerization
- Cloud Build for CI/CD

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- Firebase project with Firestore enabled
- Google Cloud Platform account with Gemini AI access

### Backend Setup
```bash
cd Backend
python -m venv BE-venv
source BE-venv/bin/activate  # On Windows: BE-venv\Scripts\activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your Firebase and GCP credentials

# Run the server
python main.py
```

### Frontend Setup
```bash
cd Frontend
npm install
npm run dev
```

The application will be available at:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 📊 API Endpoints

### Analysis
- `POST /analysis/analyze` - Submit startup data for comprehensive analysis
- `GET /analysis/{analysis_id}` - Retrieve analysis results
- `GET /analysis/{analysis_id}/status` - Check analysis progress

### Agent Chat
- `POST /agent/chat` - Interactive Q&A with AI investment advisor
- Contextual follow-up question generation
- Investment-focused conversation flow

### Documents
- `POST /documents/upload` - Upload and process startup documents
- `GET /documents/{doc_id}` - Retrieve processed document data

## 🔧 Configuration

### Environment Variables
```bash
# Firebase Configuration
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY=your-private-key
FIREBASE_CLIENT_EMAIL=your-client-email

# Google Cloud Configuration
GCP_PROJECT_ID=your-gcp-project
GCP_REGION=us-central1

# API Configuration
CORS_ORIGINS=http://localhost:5173,https://your-domain.com
```

### Firebase Setup
1. Create a Firebase project
2. Enable Firestore database
3. Generate service account credentials
4. Configure authentication rules

## 🚢 Deployment

### Using Docker
```bash
# Backend
cd Backend
docker build -t ai-startup-analyst-backend .
docker run -p 8000:8000 ai-startup-analyst-backend

# Frontend
cd Frontend
docker build -t ai-startup-analyst-frontend .
docker run -p 5173:5173 ai-startup-analyst-frontend
```

### Google Cloud Platform
The project includes Cloud Build configurations for automated deployment:
- `Backend/cloudbuild.yaml` - Backend deployment
- `Frontend/cloudbuild.yaml` - Frontend deployment

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Live Demo](https://ventureval-ef705.web.app)
- [API Documentation](https://your-api-domain.com/docs)
- [Project Issues](https://github.com/your-username/ai-startup-analyst/issues)

---

Built with ❤️ for the venture capital community