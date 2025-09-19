# services/document_processor.py
import asyncio
import aiohttp
import os
from typing import List, Dict, Any
from google import genai
from firebase_admin import storage
from PIL import Image
import json
import logging
from datetime import timedelta
from io import BytesIO
from utils.ai_client import configure_gemini
from models.database import get_storage_bucket
import re
from urllib.parse import urlparse
import fitz
from docx import Document
from PIL import Image
from settings import PROJECT_ID, GCP_REGION

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
        self.image_formats = {'.jpg', '.jpeg', '.png'}
        self.office_formats = {'.docx'}
        self.pdf_formats = {'.pdf'}
        self.text_formats = {'.txt'}

    async def generate_download_urls(self, storage_paths: List[str]) -> Dict[str, str]:
        """Convert storage paths to download URLs"""
        download_urls = {}
        bucket = get_storage_bucket()
        
        for storage_path in storage_paths:
            try:
                blob = bucket.blob(storage_path)
                
                # Check if file exists
                if not blob.exists():
                    logger.warning(f"File not found: {storage_path}")
                    continue
                
                # Generate download URL (24 hour expiry)
                download_url = blob.generate_signed_url(
                    version="v4",
                    expiration=timedelta(hours=24),
                    method="GET"
                )
                
                download_urls[storage_path] = download_url
                
            except Exception as e:
                logger.error(f"Failed to generate download URL for {storage_path}: {e}")
                continue
        
        return download_urls
    
    async def download_file(self, file_url: str) -> bytes:
        """Download file from URL with proper error handling"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise Exception(f"Failed to download file: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error downloading file {file_url}: {e}")
            raise

    def get_file_uri(self, file_path: str) -> str:
        bucket = storage.bucket()
        blob = bucket.blob(file_path)
        if not blob.exists():
            raise FileNotFoundError(f"The file '{file_path}' does not exist in Firebase Storage.")
        return f"gs://{blob.bucket.name}/{blob.name}"


    async def call_gemini_with_file(self, file_uris: list[str], prompt_text: str) -> str:
        # Build contents list: prompt first
        contents = [prompt_text]

        # Add each file with correct mime_type
        for uri in file_uris:
            ext = os.path.splitext(uri)[1].lower()
            if ext in ['.pdf']:
                mime_type = 'application/pdf'
            elif ext in ['.doc', '.docx']:
                mime_type = 'application/msword'
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
            
            if not response or not response.text:
                raise Exception("Empty synthesis response from Gemini")
            
            # Parse synthesis result
            response_text = response.text.strip()
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise Exception("No valid JSON in synthesis response")
            
            json_str = response_text[json_start:json_end]
            synthesis_result = json.loads(json_str)
            
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
                "ltv_cac_ratio": "LTV to CAC ratio (number only, null if not found)"
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
                "key_personnel": ["key team members with roles and experience"],
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
        10. Flag any inconsistencies between documents in the inconsistencies array
        11. Calculate data quality scores based on completeness and consistency
        12. Identify what critical information is missing for investment analysis
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

    async def process_single_document(self, file_name: str,  file_url: str) -> Dict:
        """Enhanced document processing with Gemini multimodal support"""
        if not self.gemini_available:
            return {'error': 'Gemini model is not available.'}

        try:
            file_content = await self.download_file(file_url)
            file_extension = self._get_file_extension(file_name)
            
            logger.info(f"Processing {file_url} with extension {file_extension}")

            if file_extension in self.image_formats:
                return await self._process_image_with_gemini(file_content, file_url)
            elif file_extension in self.pdf_formats:
                return await self._process_pdf_enhanced(file_content, file_url)
            elif file_extension in self.office_formats:
                return await self._process_office_document(file_content, file_url, file_extension)
            elif file_extension in self.text_formats:
                return await self._process_text_with_gemini(file_content.decode('utf-8'), file_url)
            else:
                return {'error': f'Unsupported file type: {file_extension}', 'file_url': file_url}

        except Exception as e:
            logger.error(f"Failed to process document {file_url}: {e}")
            return {'error': f'Critical processing failure: {str(e)}', 'file_url': file_url}

    async def _process_image_with_gemini(self, file_content: bytes, file_url: str) -> Dict:
        """Process images using Gemini Vision"""
        
        try:
            # Load image for Gemini
            image = Image.open(BytesIO(file_content))
            
            # Business document analysis prompt
            prompt = """
            You are analyzing a startup business image that could be:
            - Pitch deck slide (Problem/Solution, Market Size, Traction, Team, Financials, Competition, Business Model)
            - Financial chart or dashboard (Revenue growth, User metrics, Unit economics, Burn rate, Projections)
            - Business infographic (Market analysis, Competitive landscape, Product roadmap, Go-to-market)
            - Team slide (Founder bios, Org chart, Advisory board, Key hires)
            - Traction slide (Customer metrics, Growth charts, Partnership logos, Key achievements)
            - Product demo or screenshot (Features, UI/UX, Technical architecture)
            - Market research slide (TAM/SAM/SOM, Market trends, Customer segments)
            - Company branding (Logo, Mission statement, Company overview)

            EXTRACTION PRIORITIES:
            1. FINANCIAL METRICS: Revenue numbers, growth rates, burn rate, funding amounts, valuation, unit economics
            2. MARKET DATA: Market size (TAM/SAM/SOM), growth rates, competitive positioning
            3. TRACTION METRICS: Customer counts, user numbers, retention rates, key partnerships
            4. TEAM INFORMATION: Founder names/backgrounds, team size, key personnel, advisors
            5. PRODUCT DETAILS: Product name, features, development stage, business model
            6. OPERATIONAL DATA: Go-to-market strategy, pricing, distribution channels

            Extract comprehensive business information and return in this JSON format:
            {
                "document_type": "pitch_slide|financial_chart|traction_slide|team_slide|market_analysis|product_demo|company_overview|other",
                "slide_category": "problem_solution|market_size|business_model|traction|team|financials|competition|product|go_to_market|other",
                "company_name": "exact company name if visible",
                "sector": "specific industry vertical (FinTech, HealthTech, SaaS, AI/ML, etc.)",
                "stage": "funding stage if mentioned (seed, series_a, series_b, etc.)",
                "financials": {
                    "revenue": "annual revenue number only (null if not found)",
                    "monthly_revenue": "MRR number only (null if not found)",
                    "growth_rate": "growth rate percentage number only (null if not found)",
                    "burn_rate": "monthly burn rate number only (null if not found)",
                    "funding_raised": "total funding raised number only (null if not found)",
                    "funding_seeking": "current round amount number only (null if not found)",
                    "valuation": "company valuation number only (null if not found)",
                    "cac": "customer acquisition cost number only (null if not found)",
                    "ltv": "lifetime value number only (null if not found)",
                    "gross_margin": "gross margin percentage number only (null if not found)"
                },
                "market": {
                    "tam": "Total Addressable Market number only (null if not found)",
                    "sam": "Serviceable Addressable Market number only (null if not found)",
                    "som": "Serviceable Obtainable Market number only (null if not found)",
                    "market_growth_rate": "market growth rate percentage number only (null if not found)",
                    "target_segment": "specific target customer description",
                    "competitors": ["list of competitors mentioned"],
                    "competitive_advantage": "key differentiators mentioned"
                },
                "traction": {
                    "customers": "paying customers count number only (null if not found)",
                    "users": "total users count number only (null if not found)",
                    "mau": "monthly active users number only (null if not found)",
                    "retention_rate": "retention rate percentage number only (null if not found)",
                    "nps_score": "Net Promoter Score number only (null if not found)",
                    "partnerships": ["key partnerships mentioned"],
                    "milestones": ["key achievements listed"],
                    "growth_metrics": ["specific growth KPIs with values"]
                },
                "team": {
                    "size": "total team size number only (null if not found)",
                    "founders": ["founder names with titles and backgrounds"],
                    "key_personnel": ["key team members with roles"],
                    "advisors": ["advisory board members"],
                    "hiring_plan": ["positions planning to hire"],
                    "team_experience": "summary of relevant experience"
                },
                "product": {
                    "name": "product or service name",
                    "description": "detailed product description",
                    "stage": "development stage (concept, mvp, beta, launched, scaling)",
                    "business_model": "how the company makes money",
                    "features": ["key product features listed"],
                    "technology": "technology stack or platform mentioned",
                    "roadmap": ["product development milestones"]
                },
                "operations": {
                    "go_to_market": "sales and marketing strategy",
                    "pricing_model": "pricing strategy mentioned",
                    "distribution_channels": ["sales channels listed"],
                    "use_of_funds": "how funding will be used if mentioned"
                },
                "extracted_text": "ALL readable text from the image including headers, labels, numbers, and captions",
                "key_metrics": [
                    {"metric": "specific metric name", "value": "exact value", "unit": "unit if specified", "context": "additional context"}
                ],
                "charts_and_graphs": [
                    {"type": "chart type (bar, line, pie, etc.)", "title": "chart title", "data_points": ["key data points"], "insights": "what the chart shows"}
                ],
                "confidence_score": "0.0-1.0 based on image clarity and data completeness"
            }
            
            EXTRACTION RULES:
            1. Extract EXACT numbers as they appear - do not estimate or calculate
            2. For currency amounts, extract base number only ($5M becomes 5000000)
            3. For percentages, extract number only (25% becomes 25)
            4. Read ALL text including small print, labels, and chart annotations
            5. Identify chart types and extract data points from graphs
            6. Use null for missing numeric data, empty strings for missing text
            7. Set confidence_score based on image quality and information clarity
            8. Include context for metrics (e.g., "monthly recurring revenue" vs "annual revenue")
            9. Extract information from logos, headers, and watermarks
            10. Identify slide position indicators (e.g., "Slide 5 of 12")
            11. Note any disclaimers or footnotes that provide context
            12. Extract dates and time periods for metrics when visible
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content, 
                [prompt, image]
            )
            
            structured_data = self._parse_gemini_json_response(response.text)
            
            # Add metadata
            structured_data.update({
                'extraction_method': 'gemini_vision',
                'file_url': file_url,
                'file_type': 'image',
                'image_dimensions': f"{image.width}x{image.height}"
            })
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Gemini image processing error for {file_url}: {e}")
            return {
                'error': f'Image processing failed: {str(e)}',
                'file_url': file_url,
                'file_type': 'image'
            }

    async def _process_pdf_enhanced(self, file_content: bytes, file_url: str) -> Dict:
        """Orchestrates multi-modal analysis for a PDF document."""
        text, images = await self._extract_pdf_text_and_images(file_content)
        if not text.strip() and not images:
            return {'error': 'PDF is empty or could not be parsed', 'file_url': file_url}

        tasks = []
        if text.strip():
            tasks.append(self._process_text_with_gemini(text, file_url, "Extracted from PDF."))
        for i, img in enumerate(images):
            tasks.append(self._process_image_with_gemini(img, f"{file_url}#image_{i+1}"))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results into a single object for this document
        return self._combine_multimodal_results(results, file_url, 'pdf', len(text), len(images))

    async def _process_office_document(self, file_content: bytes, file_url: str, file_extension: str) -> Dict:
        """Orchestrates analysis for Office documents, primarily DOCX."""
        text, images = await self._extract_docx_text_and_images(file_content)
        if not text.strip() and not images:
            return {'error': 'DOCX file is empty or could not be parsed', 'file_url': file_url}
        
        tasks = []
        if text.strip():
            tasks.append(self._process_text_with_gemini(text, file_url, "Extracted from DOCX."))
        for i, img in enumerate(images):
            tasks.append(self._process_image_with_gemini(img, f"{file_url}#image_{i+1}"))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._combine_multimodal_results(results, file_url, 'docx', len(text), len(images))

    async def _process_text_with_gemini(self, text_content: str, file_url: str, extra_context: str = "") -> Dict:
        """Process text content with Gemini for enhanced structured extraction"""
        
        if not text_content.strip():
            return {'error': 'Empty text content', 'file_url': file_url}
        
        try:
            structured_data = await self.extract_structured_data(text_content, 'business_document', extra_context)
            structured_data['file_url'] = file_url # Ensure URL is in final output
            return structured_data
        except Exception as e:
            return {
                'error': f'Text processing failed: {str(e)}',
                'raw_text': text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                'file_url': file_url
            }

    def _get_file_extension(self, file_url: str) -> str:
        """Extract file extension from URL"""
        path = urlparse(file_url).path
        return os.path.splitext(path.lower())[-1]

    async def extract_structured_data(self, text: str, doc_type: str, extra_context: str = "") -> Dict:
        """Enhanced structured data extraction using Gemini"""
        
        # Limit text length to avoid token limits
        max_chars = 15000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n\n[Text truncated due to length...]"
        
        context_info = f"Context: {extra_context}\n\n" if extra_context else ""
        
        prompt = f"""
        {context_info}You are analyzing a startup {doc_type} to extract comprehensive business intelligence. Extract all relevant information for investment analysis.

        DOCUMENT CONTENT:
        {text}

        EXTRACTION FOCUS AREAS:
        1. COMPANY IDENTIFICATION: Name, sector, stage, location, founding details
        2. FINANCIAL METRICS: Revenue, growth rates, burn rate, funding, valuation, unit economics
        3. MARKET ANALYSIS: Market size (TAM/SAM/SOM), growth rates, competitive landscape
        4. TEAM COMPOSITION: Founders, key personnel, team size, experience, advisors
        5. PRODUCT DETAILS: Product description, development stage, business model, differentiation
        6. TRACTION EVIDENCE: Customer metrics, user growth, partnerships, milestones
        7. OPERATIONAL DATA: Go-to-market strategy, pricing, distribution, use of funds

        Return a comprehensive JSON object with this exact structure:
        {{
            "company_name": "exact company name as written",
            "sector": "specific industry vertical (FinTech, HealthTech, SaaS, AI/ML, E-commerce, etc.)",
            "stage": "funding stage (pre-seed, seed, series_a, series_b, series_c, growth, etc.)",
            "geography": "headquarters location and primary markets",
            "founded": "founding year if mentioned",
            "description": "comprehensive company description including problem and solution",
            "financials": {{
                "revenue": "annual revenue number only (null if not found)",
                "monthly_revenue": "MRR number only (null if not found)",
                "growth_rate": "annual growth rate percentage number only (null if not found)",
                "monthly_growth_rate": "MoM growth rate percentage number only (null if not found)",
                "burn_rate": "monthly burn rate number only (null if not found)",
                "funding_raised": "total funding raised number only (null if not found)",
                "funding_seeking": "current round amount number only (null if not found)",
                "valuation": "company valuation number only (null if not found)",
                "runway_months": "months of runway number only (null if not found)",
                "gross_margin": "gross margin percentage number only (null if not found)",
                "cac": "customer acquisition cost number only (null if not found)",
                "ltv": "lifetime value number only (null if not found)",
                "ltv_cac_ratio": "LTV to CAC ratio number only (null if not found)"
            }},
            "market": {{
                "tam": "Total Addressable Market number only (null if not found)",
                "sam": "Serviceable Addressable Market number only (null if not found)",
                "som": "Serviceable Obtainable Market number only (null if not found)",
                "target_segment": "specific target customer segments and personas",
                "market_growth_rate": "market growth rate percentage number only (null if not found)",
                "competitors": ["list of direct and indirect competitors mentioned"],
                "competitive_positioning": "how company differentiates from competitors",
                "market_trends": ["key market trends and drivers mentioned"]
            }},
            "team": {{
                "size": "total team size number only (null if not found)",
                "founders": ["founder names with titles and backgrounds"],
                "key_personnel": ["key team members with roles and experience"],
                "advisors": ["advisory board members and their backgrounds"],
                "hiring_plan": ["key positions planning to hire"],
                "team_experience": "summary of team's relevant experience and expertise"
            }},
            "product": {{
                "name": "product or service name",
                "description": "detailed product description and functionality",
                "stage": "development stage (concept, mvp, beta, launched, scaling, mature)",
                "business_model": "detailed business model and revenue streams",
                "competitive_advantage": "key differentiators and competitive moats",
                "technology_stack": "technology platform and technical details",
                "intellectual_property": "patents, trademarks, or proprietary technology",
                "product_roadmap": ["key development milestones and timeline"]
            }},
            "traction": {{
                "customers": "paying customers count number only (null if not found)",
                "users": "total active users number only (null if not found)",
                "mau": "monthly active users number only (null if not found)",
                "retention_rate": "customer retention rate percentage number only (null if not found)",
                "nps_score": "Net Promoter Score number only (null if not found)",
                "partnerships": ["strategic partnerships and their significance"],
                "milestones": ["key achievements and milestones reached"],
                "customer_testimonials": ["notable customer feedback or case studies"],
                "growth_metrics": ["specific KPIs with values and growth rates"]
            }},
            "funding": {{
                "previous_rounds": ["details of previous funding rounds with amounts and investors"],
                "current_round": "details of current funding round being raised",
                "use_of_funds": "how the funding will be used",
                "investors": ["current investors and their involvement"],
                "board_composition": ["board members and their backgrounds"]
            }},
            "operations": {{
                "go_to_market": "go-to-market strategy and sales approach",
                "pricing_strategy": "pricing model and strategy",
                "distribution_channels": ["sales and distribution channels"],
                "unit_economics": "unit economics breakdown if available",
                "key_metrics": ["important operational KPIs and their values"]
            }},
            "risks_and_challenges": {{
                "market_risks": ["market-related risks mentioned"],
                "competitive_risks": ["competitive threats identified"],
                "operational_risks": ["operational challenges mentioned"],
                "financial_risks": ["financial risks or concerns noted"]
            }},
            "confidence_score": "0.0-1.0 based on information completeness and clarity"
        }}

        EXTRACTION RULES:
        1. Extract EXACT numbers as they appear - do not estimate, calculate, or round
        2. For currency amounts, extract base number only ($5M becomes 5000000, $500K becomes 500000)
        3. For percentages, extract number only (25% becomes 25, 2.5% becomes 2.5)
        4. Use null for missing numeric data, empty strings for missing text, empty arrays for missing lists
        5. Company name must be exactly as written in the document
        6. Sector should be specific industry vertical, not generic terms
        7. Stage should match standard funding terminology
        8. Include context and timeframes for metrics when available
        9. Extract information from tables, bullet points, and structured data
        10. Identify and extract key performance indicators and their values
        11. Note any disclaimers or assumptions mentioned
        12. Extract dates and time periods associated with metrics
        13. Confidence score should reflect data quality and completeness
        """
        
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            
            if not response or not response.text:
                raise Exception("Empty response from Gemini")
            
            structured_data = self._parse_gemini_json_response(response.text)
            
            # Add processing metadata
            structured_data.update({
                'extraction_method': 'gemini_structured',
                'raw_text_length': len(text),
                'document_type': doc_type
            })
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Gemini structured extraction failed: {e}")
            return {
                'error': f'Structured extraction failed: {str(e)}',
                'raw_text': text[:1000] + "..." if len(text) > 1000 else text,
                'extraction_method': 'failed'
            }

    async def synthesize_response(self, gemini_response, docs_processed: int) -> Dict:
        """Enhanced document synthesis using Gemini"""
        
        if not gemini_response:
            return {'error': 'No gemini response to synthesize'}
        
        # Create synthesis prompt
        data_str = json.dumps(gemini_response, indent=2)
        max_chars = 10000
        if len(data_str) > max_chars:
            data_str = data_str[:max_chars] + "\n... [data truncated for processing]"
        
        prompt = f"""
        Synthesize data from {docs_processed} business documents. Cross-reference information and create a unified view.

        Document data:
        {data_str}

        Create a comprehensive synthesis in this JSON format:
        {{
            "synthesized_data": {{
                "company_name": "",
                "sector": "",
                "stage": "",
                "geography": "",
                "founded": "",
                "description": "",
                "financials": {{
                    "revenue": null,
                    "growth_rate": null,
                    "burn_rate": null,
                    "funding_raised": null,
                    "funding_seeking": null,
                    "valuation": null,
                    "runway_months": null
                }},
                "market": {{
                    "size": null,
                    "target_segment": "",
                    "competitors": [],
                    "growth_rate": null
                }},
                "team": {{
                    "size": null,
                    "founders": [],
                    "key_personnel": []
                }},
                "product": {{
                    "name": "",
                    "description": "",
                    "stage": "",
                    "business_model": "",
                    "competitive_advantage": ""
                }},
                "traction": {{
                    "customers": null,
                    "users": null,
                    "partnerships": [],
                    "key_metrics": []
                }}
            }},
            "data_quality": {{
                "consistency_score": 0.0,
                "completeness_score": 0.0,
                "confidence_score": 0.0,
                "inconsistencies": [],
                "missing_critical_data": []
            }},
            "source_summary": {{
                "documents_processed": {docs_processed},
                "primary_sources": [],
                "data_coverage": {{}}
            }}
        }}

        Synthesis rules:
        1. Prioritize data appearing in multiple sources
        2. Flag conflicts in inconsistencies array  
        3. Calculate scores based on data quality and consistency
        4. Don't invent information - only use what's provided
        5. Identify missing critical business data
        """
        
        try:
            if not self.model:
                raise Exception("Gemini not available for synthesis")

            response = await asyncio.to_thread(self.model.models.generate_content, model="gemini-2.5-flash", contents=[prompt])
            
            if not response or not response.text:
                raise Exception("Empty synthesis response from Gemini")
            
            # Parse synthesis result
            response_text = response.text.strip()
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                raise Exception("No valid JSON in synthesis response")
            
            json_str = response_text[json_start:json_end]
            synthesis_result = json.loads(json_str)
            
            # Add processing metadata
            synthesis_result['processing_info'] = {
                'documents_processed': docs_processed,
                'synthesis_method': 'gemini_enhanced'
            }
            
            return synthesis_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Synthesis JSON parsing error: {e}")
            return {
                'error': f'Synthesis parsing failed: {str(e)}',
                'individual_results': gemini_response,
            }
        except Exception as e:
            logger.error(f"Document synthesis failed: {e}")
            return {
                'error': f'Document synthesis failed: {str(e)}',
                'individual_results': gemini_response,
            }

    async def _extract_pdf_text_and_images(self, file_content: bytes) -> tuple[str, list[bytes]]:
        """Extracts both text and images from a PDF, returning (full_text, list_of_image_bytes)."""
        text_parts, image_bytes_list = [], []
        try:
            doc = fitz.open(stream=file_content, filetype="pdf")
            for page_num, page in enumerate(doc):
                text_parts.append(f"--- Page {page_num + 1} ---\n{page.get_text()}")
                for img in page.get_images(full=True):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes_list.append(base_image["image"])
            return "\n\n".join(text_parts), image_bytes_list
        except Exception as e:
            logger.error(f"Error processing PDF with PyMuPDF: {e}")
            return "", []

    async def _extract_docx_text_and_images(self, file_content: bytes) -> tuple[str, list[bytes]]:
        """Extracts both text and images from a DOCX, returning (text, list_of_image_bytes)."""
        try:
            doc_stream = BytesIO(file_content)
            doc = Document(doc_stream)
            text_content = "\n".join([para.text for para in doc.paragraphs])
            image_bytes_list = [rel.target_part.blob for rel in doc.part.rels.values() if "image" in rel.target_ref]
            return text_content, image_bytes_list
        except Exception as e:
            logger.error(f"Failed to extract content from DOCX: {e}")
            return "", []

    def _combine_multimodal_results(self, results: List[Any], url: str, ftype: str, tlen: int, ilen: int) -> Dict:
        """Helper to combine text and image analysis results for a single document."""
        text_analysis, image_analyses, errors = {}, [], []
        for res in results:
            if isinstance(res, Exception):
                errors.append(str(res))
            elif 'error' in res:
                errors.append(res['error'])
            elif res.get('extraction_method') == 'gemini_vision':
                image_analyses.append(res)
            else:
                text_analysis = res
        
        return {
            'file_url': url,
            'file_type': ftype,
            'extraction_method': 'multi-modal_enhanced',
            'text_based_analysis': text_analysis,
            'image_based_analyses': image_analyses,
            'processing_errors': errors,
            'summary': f'Extracted {tlen} text chars and {ilen} images.'
        }

    def _parse_gemini_json_response(self, response_text: str) -> Dict:
        """
        Parses JSON from a Gemini response using a robust regex method,
        handles errors gracefully, and enforces a consistent output schema.
        """
        try:
            # 1. Use the robust regex from Function 2 to find the JSON string
            # json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            json_match = re.search(r'```json\s*(\{([^\}]*)\})\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Fallback for responses that aren't in a markdown block
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start == -1 or json_end == 0:
                    raise ValueError("No valid JSON object found in the response.")
                json_str = response_text[json_start:json_end]

            # 2. Parse the extracted string
            parsed_data = json.loads(json_str)

            # 3. Enforce the schema with defaults, like in Function 1
            default_structure = {
                'company_name': '', 'sector': '', 'stage': '', 'revenue': None,
                'growth_rate': None, 'team_size': None, 'funding_raised': None,
                'funding_seeking': None, 'market_size': None, 'problem': '',
                'solution': '', 'business_model': '', 'traction_metrics': [],
                'founders': [], 'competitors': [], 'key_partnerships': [],
                'confidence_score': 0.5
            }
            
            # Merge parsed data into the default structure
            # This ensures all keys exist in the final output
            final_data = default_structure.copy()
            final_data.update(parsed_data)
            
            return final_data

        except (json.JSONDecodeError, ValueError) as e:
            # 4. Catch errors and return a structured error response, like in Function 1
            logger.error(f"Failed to parse Gemini response: {e}")
            return {
                'error': f'Could not parse structured data from response: {str(e)}',
                'raw_response': response_text[:500] + "..." if len(response_text) > 500 else response_text
            }
