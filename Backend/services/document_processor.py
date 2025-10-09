# services/document_processor.py
import asyncio
import time
import uuid
import aiohttp
import os
from typing import List, Dict, Any
from google import genai
from firebase_admin import storage, firestore

import json
import logging
from datetime import timedelta
from pathlib import Path
from io import BytesIO
from utils.ai_client import configure_gemini
from models.database import get_storage_bucket
import re
from urllib.parse import urlparse
from settings import PROJECT_ID, GCP_REGION
from utils.enhanced_text_cleaner import sanitize_for_frontend
from utils.helpers import db_insert
from models.database import get_firestore_client
from constants import Collections, ALLOWED_EXTENSIONS
from exceptions import NotFoundException, ServerException, InvalidParametersException

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
        A comprehensive document processor that handles text, images, PDFs, and DOCX files
        with multi-modal analysis capabilities using the Gemini API.
        """
    def __init__(self):
        self.gemini_available = configure_gemini()
        if self.gemini_available:
            self.model = genai.Client(
                vertexai=True,
                project=PROJECT_ID,
                location=GCP_REGION
            )
            logger.info("DocumentProcessor initialized with Gemini multimodal support")
        else:
            logger.warning("Gemini not available - using basic text processing only")
            self.model = None
        
        # File type classifications

    def get_file_uri(self, file_path: str) -> str:
        bucket = storage.bucket()
        blob = bucket.blob(file_path)
        if not blob.exists():
            raise FileNotFoundError(f"The file '{file_path}' does not exist in Firebase Storage.")
        return f"gs://{blob.bucket.name}/{blob.name}"

    async def call_gemini_with_file(self, file_uris: list[str], prompt_text: str) -> Dict:
        # Build contents list: prompt first
        contents = [prompt_text]

        # Add each file with correct mime_type
        for uri in file_uris:
            ext = os.path.splitext(uri)[1].lower()
            if ext in ['.pdf']:
                mime_type = 'application/pdf'
            elif ext in ['.txt']:
                mime_type = 'text/plain'
            elif ext in ['.jpg', '.jpeg']:
                mime_type = 'image/jpeg'
            elif ext in ['.png']:
                mime_type = 'image/png'
            else:
                raise ValueError(f"Unsupported file type: {ext}")

            contents.append({
                "uri": uri,
                "mime_type": mime_type
            })

        try:
            response = await asyncio.to_thread(self.model.models.generate_content, model="gemini-2.5-flash", contents=contents)
            
            if not response or not hasattr(response, 'text') or not response.text:
                logger.error(f"Empty synthesis response from Gemini while processing documents")
                raise Exception("Empty synthesis response from Gemini")
            try:
                synthesis_result = sanitize_for_frontend(response.text.strip())
            except Exception as error:
                logger.error(f"Response parsing error while processing file read response: {str(error)}")
                raise Exception(f"Response parsing error while processing file read response: {str(error)}")

            
            # Add processing metadata
            synthesis_result['processing_info'] = {
                'documents_processed': len(file_uris),
                'synthesis_method': 'gemini_enhanced'
            }
            
            return synthesis_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Synthesis JSON parsing error: {e}")
            return {
                'error': f'Synthesis parsing failed: {str(e)}',
            }
        except Exception as e:
            logger.error(f"Document synthesis failed: {e}")
            return {
                'error': f'Document synthesis failed: {str(e)}',
            }

    # TODO: improve prompt and clean function
    async def process_documents_from_storage(self, storage_paths: List[str]) -> Dict:
        """Process documents from Firebase Storage paths"""
        
        if not storage_paths:
            return {'error': 'No storage paths provided'}

        file_uris = [self.get_file_uri(path) for path in storage_paths]
        prompt = """
        You are analyzing startup pitch deck materials, business documents, and financial data. Extract comprehensive structured data following this exact JSON schema.

        DOCUMENT TYPES TO ANALYZE:
        - Pitch deck slides: Problem/Solution, Market Size, Business Model, Traction, Team, Financials, Competition, Go-to-Market
        - Financial projections: Revenue forecasts, P&L statements, cash flow, unit economics, KPI dashboards
        - Business plans: Executive summaries, market analysis, competitive landscape, operational plans
        - Team information: Founder bios, org charts, advisory boards, key hires
        - Traction data: Customer metrics, user growth, revenue charts, partnership announcements
        - Market research: TAM/SAM/SOM analysis, competitive analysis, market trends
        - Product information: Feature lists, roadmaps, technical specifications, user feedback

        EXTRACTION GUIDELINES:
        1. FINANCIAL DATA: Extract exact numbers from charts, tables, and text. Look for:
           - Current revenue (ARR, MRR, quarterly, annual)
           - Growth rates (MoM, YoY, CAGR)
           - Burn rate (monthly cash burn)
           - Funding amounts (seed, Series A/B/C, total raised)
           - Valuation (pre-money, post-money, target)
           - Unit economics (CAC, LTV, gross margins)
           - Runway calculations
           - Revenue projections: Extract historical and future revenue data by year from charts, tables, financial models
           - Look for revenue forecasts, P&L statements, cash flow projections showing year-over-year revenue
           - Include both past performance and future projections (e.g., 2022: $500K, 2023: $1M, 2024: $2.5M)

        2. MARKET DATA: Extract market sizing and competitive information:
           - TAM/SAM/SOM with specific dollar amounts
           - Market growth rates and trends
           - Competitive landscape and positioning
           - Target customer segments and personas

        3. TEAM DATA: Identify all team members and organizational structure:
           - Founder names, titles, backgrounds, previous experience
           - Team size and key roles (engineering, sales, marketing, operations)
           - Advisory board members and investors
           - Hiring plans and key positions to fill

        4. PRODUCT DATA: Extract product and business model details:
           - Product name, description, and key features
           - Development stage (concept, MVP, beta, launched, scaling)
           - Business model (SaaS, marketplace, e-commerce, etc.)
           - Revenue streams and pricing strategy
           - Competitive advantages and differentiation

        5. TRACTION DATA: Extract all growth and customer metrics:
           - Customer counts (paying customers, enterprise clients)
           - User metrics (MAU, DAU, registered users)
           - Revenue metrics (MRR, ARR, revenue per customer)
           - Growth metrics (user growth rate, revenue growth rate)
           - Partnerships and strategic relationships
           - Key milestones and achievements

        OUTPUT ONLY THIS JSON STRUCTURE:
        {
        "synthesized_data": {
            "company_name": "exact company name as written in documents",
            "sector": "specific industry vertical (e.g., FinTech, HealthTech, SaaS, E-commerce, AI/ML, etc.)",
            "stage": "funding stage (pre-seed, seed, series_a, series_b, series_c, growth, etc.)",
            "geography": "primary market and headquarters location (city, country)",
            "founded": "founding year (YYYY format)",
            "description": "comprehensive 3-4 sentence company description including problem solved and solution approach",
            "financials": {
                "revenue": "current annual revenue in USD (number only, null if not found)",
                "monthly_revenue": "current MRR in USD (number only, null if not found)",
                "growth_rate": "annual revenue growth rate as percentage (number only, null if not found)",
                "monthly_growth_rate": "month-over-month growth rate as percentage (number only, null if not found)",
                "burn_rate": "monthly cash burn in USD (number only, null if not found)",
                "funding_raised": "total funding raised to date in USD (number only, null if not found)",
                "funding_seeking": "amount seeking in current round in USD (number only, null if not found)",
                "valuation": "current or target valuation in USD (number only, null if not found)",
                "runway_months": "months of runway remaining (number only, null if not found)",
                "gross_margin": "gross margin percentage (number only, null if not found)",
                "cac": "customer acquisition cost in USD (number only, null if not found)",
                "ltv": "lifetime value per customer in USD (number only, null if not found)",
                "ltv_cac_ratio": "LTV to CAC ratio (number only, null if not found)",
                "revenue_projections": "list of dictionaries with year and revenue data for historical and projected revenue (e.g., [{'year': 2022, 'number': 500000}, {'year': 2023, 'number': 1000000}, {'year': 2024, 'number': 2500000}], null if not found)"
            },
            "market": {
                "size": "Total Addressable Market (TAM) in USD (number only, null if not found)",
                "sam": "Serviceable Addressable Market in USD (number only, null if not found)",
                "som": "Serviceable Obtainable Market in USD (number only, null if not found)",
                "target_segment": "specific target customer segment and personas",
                "competitors": ["list of direct and indirect competitors mentioned"],
                "growth_rate": "market growth rate percentage annually (number only, null if not found)",
                "market_trends": ["key market trends and drivers mentioned"],
                "competitive_positioning": "how company positions against competitors"
            },
            "team": {
                "size": "total team size including founders (number only, null if not found)",
                "founders": ["founder names with titles and brief background"],
                "key_hires": ["key team members with roles and experience"],
                "advisors": ["advisory board members and their backgrounds"],
                "hiring_plan": ["key positions planning to hire"],
                "team_experience": "summary of team's relevant experience and expertise"
            },
            "product": {
                "name": "product or service name",
                "description": "detailed description of what the product does and how it works",
                "stage": "development stage (concept, mvp, beta, launched, scaling, mature)",
                "business_model": "detailed business model and revenue streams",
                "competitive_advantage": "key differentiators and competitive moats",
                "technology_stack": "technology platform and key technical details if mentioned",
                "intellectual_property": "patents, trademarks, or proprietary technology mentioned",
                "product_roadmap": ["key product development milestones and timeline"]
            },
            "traction": {
                "customers": "number of paying customers (number only, null if not found)",
                "users": "total active users (number only, null if not found)",
                "mau": "monthly active users (number only, null if not found)",
                "partnerships": ["strategic partnerships and their significance"],
                "key_metrics": ["important KPIs with specific values and context"],
                "milestones": ["key achievements and milestones reached"],
                "customer_testimonials": ["notable customer feedback or case studies"],
                "retention_rate": "customer or user retention rate percentage (number only, null if not found)",
                "nps_score": "Net Promoter Score (number only, null if not found)"
            },
            "funding": {
                "previous_rounds": ["details of previous funding rounds with amounts and investors"],
                "current_round": "details of current funding round being raised",
                "use_of_funds": "how the funding will be used",
                "investors": ["current investors and their involvement"],
                "board_composition": ["board members and their backgrounds"]
            },
            "operations": {
                "business_metrics": ["key operational metrics and KPIs"],
                "go_to_market": "go-to-market strategy and sales approach",
                "distribution_channels": ["sales and distribution channels"],
                "pricing_strategy": "pricing model and strategy",
                "unit_economics": "unit economics breakdown if available"
            }
        },
        "data_quality": {
            "consistency_score": "score 0.0-1.0 based on data consistency across documents",
            "completeness_score": "score 0.0-1.0 based on how much critical data is available",
            "confidence_score": "score 0.0-1.0 based on clarity and reliability of extracted data",
            "inconsistencies": ["list any conflicting information found across documents"],
            "missing_critical_data": ["list critical business data that is missing or unclear"],
            "data_sources": ["types of documents that provided the most valuable information"]
        },
        "source_summary": {
            "documents_processed": "number of documents analyzed",
            "primary_sources": ["most valuable document types for data extraction"],
            "data_coverage": {
                "financials": "percentage of financial data fields populated",
                "market": "percentage of market data fields populated", 
                "team": "percentage of team data fields populated",
                "product": "percentage of product data fields populated",
                "traction": "percentage of traction data fields populated"
            }
        }
        }

        CRITICAL EXTRACTION RULES:
        1. Extract EXACT numbers as they appear - do not estimate, calculate, or round
        2. For currency amounts, extract the base number only (e.g., "$5M" becomes 5000000)
        3. For percentages, extract the number only (e.g., "25%" becomes 25)
        4. Use null for missing numeric data, empty string for missing text, empty array for missing lists
        5. If multiple values exist for the same metric, use the most recent or prominently displayed
        6. Company name must be exactly as written in the documents
        7. Sector should be specific (not just "Technology" but "FinTech" or "AI/ML")
        8. Stage should match standard funding terminology
        9. Extract ALL readable text from charts, graphs, and financial projections
        10. For revenue projections: Extract year-over-year revenue data from charts, tables, financial models
            - Look for historical revenue data (past 2-3 years) and future projections (next 3-5 years)
            - Format as [{"year": YYYY, "number": revenue_amount}, {"year": YYYY, "number": revenue_amount}]
            - Include related terms: "revenue forecast", "annual revenue", "projected revenue", "revenue model"
            - Extract from pitch deck financial slides, business plan projections, P&L statements
        11. Flag any inconsistencies between documents in the inconsistencies array
        12. Calculate data quality scores based on completeness and consistency
        13. Identify what critical information is missing for investment analysis
        """

        try:
            synthesized = await  self.call_gemini_with_file(file_uris, prompt)
            return synthesized
        except Exception as e:
            logger.error(f"Document synthesis failed: {e}")
            return {
                'error': f'Document synthesis failed: {str(e)}',
            }        
        # Synthesize all documents with Gemini

    def _get_file_extension(self, file_url: str) -> str:
        """Extract file extension from URL"""
        path = urlparse(file_url).path
        return os.path.splitext(path.lower())[-1]

class DocumentService:
    def __init__(self, db=None):
        self.db = db or get_firestore_client()
        self.bucket = get_storage_bucket()

    async def fetch_document_details_from_db(self, document_ids, user_id, analysis_id):
        query = self.db.collection(Collections.DOCUMENTS)
        if document_ids:
            query = query.where(
            "document_id", "in", document_ids
        )

        if user_id:
            query = query.where(
                "user_id", "==", user_id
            )
        if analysis_id:
            query = query.where(
                "analysis_id", "==", analysis_id
            )
        query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
        try:
            results = query.stream()
            
            # 5. Process and Return Data
            mappings = []
            for doc in results:
                data = doc.to_dict()
                data['id'] = doc.id # Include the document ID for reference
                mappings.append(data)
                
            logger.info(f"Retrieved {len(mappings)} documents for user {user_id} and documents_ids: {document_ids}")
            return mappings
        except Exception as error:
            logger.error(f"Error fetching document_details: {document_ids}: {error}")
            raise ServerException


    async def generate_download_url(self, document: dict):
        storage_path = document["storage_path"]
        try:
            blob = self.bucket.blob(storage_path)

            # Check if file exists
            if not blob.exists():
                logger.warning(f"File not found: {storage_path}")

            # Generate download URL (30 minutes expiry)
            download_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=30),
                method="GET"
            )

            document["download_url"] = download_url

        except Exception as e:
            logger.error(f"Failed to generate download URL for {storage_path}: {e}")
        return document

    async def get_document_details(self, document_ids: List[str], user_id: str, analysis_id: str = None, is_download_url_required: bool = False) -> Dict[str, str]:
        """Convert storage paths to download URLs"""
        documents = await self.fetch_document_details_from_db(document_ids, user_id, analysis_id)
        if document_ids and not documents:
            raise NotFoundException(message="File does not exist")
        if is_download_url_required:
            download_url_tasks = [self.generate_download_url(document) for document in documents]
            documents = await asyncio.gather(*download_url_tasks)
        return documents
    

    async def generate_presigned_url(self, payload, user_id):
        try:
            # Step 1: Validate the file metadata from the payload
            file_extension = Path(payload.filename).suffix.lower()
            
            # Validate file extension
            if file_extension not in ALLOWED_EXTENSIONS:
                raise InvalidParametersException(message=f"Invalid file extension: {file_extension}. Supported extensions: .pdf, .txt, .jpg, .jpeg, .png")

            # Step 2: Generate a unique path in Firebase Storage
            document_id = str(uuid.uuid4())
            timestamp = int(time.time())
            filename_without_ext = Path(payload.filename).stem
            storage_path = f"documents/{payload.file_type.value}/{timestamp}_{filename_without_ext}_{document_id}{file_extension}"
            data_to_insert = {
                "document_id": document_id,
                "storage_path": storage_path,
                "file_name": payload.filename,
                "user_id": user_id
            }
            await db_insert(document_id, Collections.DOCUMENTS, data_to_insert)
            
            # Step 3: Generate the V4 Signed URL
            bucket = get_storage_bucket()
            blob = bucket.blob(storage_path)

            # The frontend MUST use a PUT payload with the exact content_type specified here.
            signed_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=15),
                method="PUT",
            )

            return {
                "success": True,
                "signed_url": signed_url,
                "storage_path": storage_path,
                "document_id": document_id,
                "file_type": payload.file_type.value,
                "message": "Upload URL generated successfully. Use PUT to upload the file."
            }
        except Exception as error:
            logger.error(f"Exception while generating presigned url: {error}")
            raise ServerException

