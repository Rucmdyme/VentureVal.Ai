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
                project="ventureval-ef705",
                location="us-central1"
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


    def call_gemini_with_file(self, file_uris: list[str], prompt_text: str) -> str:
        client = genai.Client(
            vertexai=True,
            project="ventureval-ef705",
            location="us-central1"
        )

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

        # Send request
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents
        )

        return response.text
    
    # TODO: improve prompt and clean function
    async def process_documents_from_storage(self, storage_paths: List[str]) -> Dict:
        """Process documents from Firebase Storage paths"""
        
        if not storage_paths:
            return {'error': 'No storage paths provided'}

        file_uris = [self.get_file_uri(path) for path in storage_paths]
        prompt = """
            Extract structured business data from the attached PDF.
            Output ONLY valid JSON following this schema exactly.
            Do NOT explain your process or invent information.
            Document could be:
            - A presentation slide or pitch deck page
            - A business chart, graph, or infographic
            - A scanned business document
            - A screenshot of financial data or metrics
            - A company logo or branding material

            {
            "synthesized_data": {
                "company_name": "",
                "sector": "",
                "stage": "",
                "geography": "",
                "founded": "",
                "description": "",
                "financials": {
                    "revenue": null,
                    "growth_rate": null,
                    "burn_rate": null,
                    "funding_raised": null,
                    "funding_seeking": null,
                    "valuation": null,
                    "runway_months": null
                },
                "market": {
                    "size": null,
                    "target_segment": "",
                    "competitors": [],
                    "growth_rate": null
                },
                "team": {
                    "size": null,
                    "founders": [],
                    "key_personnel": []
                },
                "product": {
                    "name": "",
                    "description": "",
                    "stage": "",
                    "business_model": "",
                    "competitive_advantage": ""
                },
                "traction": {
                    "customers": null,
                    "users": null,
                    "partnerships": [],
                    "key_metrics": []
                }
            },
            "data_quality": {
                "consistency_score": 0.0,
                "completeness_score": 0.0,
                "confidence_score": 0.0,
                "inconsistencies": [],
                "missing_critical_data": []
            },
            "source_summary": {
                "documents_processed": 1,
                "primary_sources": [],
                "data_coverage": {}
            }
            }
            Synthesis rules:
            1. Prioritize data appearing in multiple sources
            2. Flag conflicts in inconsistencies array
            3. Calculate scores based on data quality and consistency
            4. Don't invent information - only use what's provided
            5. Identify missing critical business data
            """

        # TODO: remove after debugging to fetch accurate data
        await asyncio.sleep(5)
        # gemini_response = self.call_gemini_with_file(file_uris, prompt)
        gemini_response = '```json\n{\n  "synthesized_data": {\n    "company_name": "Sia",\n    "sector": "AI and Data Analytics",\n    "stage": "Seed",\n    "geography": "Global (headquartered in Bengaluru, India)",\n    "founded": "2022",\n    "description": "Sia is an Agentic AI for Data Analytics developed by Datastride Analytics. It aims to democratize data analysis by providing a simple chat interface that brings a full data team experience to everyone in an organization. The product focuses on simplifying data analytics, reducing the cost of AI adoption, and unifying organizational data processes through features like recommender engines, auto visualizations, no-code model building, and unified data integration.",\n    "financials": {\n      "revenue": 400000.0,\n      "growth_rate": 0.43,\n      "burn_rate": 16867.0,\n      "funding_raised": 520964.0,\n      "funding_seeking": 602410.0,\n      "valuation": null,\n      "runway_months": 6\n    },\n    "market": {\n      "size": 300000000000.0,\n      "target_segment": "Medium to large enterprises (500+ employees, $5M+ revenue) handling large volumes of data and using legacy systems.",\n      "competitors": [\n        "Alteryx",\n        "Dataiku",\n        "Obviously.AI"\n      ],\n      "growth_rate": 0.43\n    },\n    "team": {\n      "size": null,\n      "founders": [\n        "Divya Krishna R",\n        "Sumalata Kamat",\n        "Karthik C"\n      ],\n      "key_personnel": []\n    },\n    "product": {\n      "name": "Sia",\n      "description": "Sia is an Agentic AI solution providing a generative AI-driven chat interface for data analytics. Key features include quick analytics widgets, instant data transformations, scalable data pipelines, custom code integration, feature readability, AI guidance, conversational AI, automated charts, AI deep thinking, and unified data integration from various sources. It uses a multi-agent architecture (swarm and solo agents) and supports flexible deployment (on-premise, hybrid, or cloud).",\n      "stage": "Early product deployment / early traction",\n      "business_model": "Subscription fees (monthly/annual), one-time setup/deployment fees for on-premise solutions, annual maintenance fees, and marketplace commissions from selling data-based solutions.",\n      "competitive_advantage": "Democratization of AI & Data through a simple chat interface, context-aware insights, minimized bottlenecks, high margins due to client bearing infrastructure costs, established product, readily deployable, strong partnerships, and low R&D costs."\n    },\n    "traction": {\n      "customers": 5,\n      "users": null,\n      "partnerships": [\n        "Microsoft for Startups",\n        "NSRCEL (IIMB)",\n        "Vetrina",\n        "Saudi Telecom",\n        "Sobha group",\n        "Accolade",\n        "HDFCergo",\n        "Pfizer",\n        "Maruti Suzuki",\n        "Tata Elxsi",\n        "PROPEL ATHON",\n        "Data Services",\n        "primeNumber",\n        "Bosch",\n        "RayRC"\n      ],\n      "key_metrics": [\n        {\n          "metric": "Booked Revenue",\n          "value": "400,000 USD"\n        },\n        {\n          "metric": "Sales Pipeline Value",\n          "value": "400,000 USD"\n        },\n        {\n          "metric": "Projected Growth Opportunities",\n          "value": "4,000,000 USD"\n        },\n        {\n          "metric": "Client Lifetime Value (LTV)",\n          "value": ">1,000,000 USD"\n        },\n        {\n          "metric": "LTV:CAC Ratio",\n          "value": "Minimum 10"\n        },\n        {\n          "metric": "Profit After Tax (PAT)",\n          "value": "Minimum 30%"\n        },\n        {\n          "metric": "Time to Insights reduction",\n          "value": "90%"\n        },\n        {\n          "metric": "Volume of Data Processed increase",\n          "value": "10x"\n        },\n        {\n          "metric": "Data Analytics Budget reduction",\n          "value": "4x"\n        },\n        {\n          "metric": "Project Deployment Time saved",\n          "value": "80%"\n        }\n      ]\n    }\n  },\n  "data_quality": {\n    "consistency_score": 0.95,\n    "completeness_score": 0.7,\n    "confidence_score": 0.9,\n    "inconsistencies": [\n      "Market size growth rate for \'Global Data Analytics\' is 13% CAGR on slide 9, but an external source mentioned in the textual document for \'Big Data Analytics Market\' is 13.5% CAGR to $725.93 Billion by 2031. The data from slide 9, which is more specific to the company\'s niche (\'Agentic AI market\'), has been prioritized."\n    ],\n    "missing_critical_data": [\n      "Valuation",\n      "Total team size",\n      "Number of active users",\n      "Specific Annual Recurring Revenue (ARR) or Monthly Recurring Revenue (MRR)"\n    ]\n  },\n  "source_summary": {\n    "documents_processed": 1,\n    "primary_sources": [\n      "PDF Document (15 slides + 9 textual pages)"\n    ],\n    "data_coverage": {\n      "company_name": "Explicit",\n      "sector": "Explicit",\n      "stage": "Explicit",\n      "geography": "Inferred/Explicit",\n      "founded": "Explicit",\n      "description": "Synthesized",\n      "financials.revenue": "Explicit (booked/current) and projected",\n      "financials.growth_rate": "Explicit (market)",\n      "financials.burn_rate": "Explicit",\n      "financials.funding_raised": "Explicit (multiple sources combined)",\n      "financials.funding_seeking": "Explicit",\n      "financials.valuation": "Missing",\n      "financials.runway_months": "Explicit",\n      "market.size": "Explicit (TAM/SOM)",\n      "market.target_segment": "Explicit",\n      "market.competitors": "Explicit",\n      "market.growth_rate": "Explicit",\n      "team.size": "Missing",\n      "team.founders": "Explicit",\n      "team.key_personnel": "Missing",\n      "product.name": "Explicit",\n      "product.description": "Synthesized",\n      "product.stage": "Explicit",\n      "product.business_model": "Explicit",\n      "product.competitive_advantage": "Synthesized/Explicit",\n      "traction.customers": "Explicit (count)",\n      "traction.users": "Missing",\n      "traction.partnerships": "Explicit",\n      "traction.key_metrics": "Explicit"\n    }\n  }\n}\n```'        
        
        # Synthesize all documents with Gemini
        try:
            synthesized = await self.synthesize_response(gemini_response, len(file_uris))
            return synthesized
        except Exception as e:
            logger.error(f"Document synthesis failed: {e}")
            return {
                'error': f'Document synthesis failed: {str(e)}',
                'individual_results': gemini_response,
            }

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
            Analyze this image which could be:
            - A presentation slide or pitch deck page
            - A business chart, graph, or infographic  
            - A scanned business document
            - A screenshot of financial data or metrics
            - A company logo or branding material
            
            Extract all business-relevant information and return in this JSON format:
            {
                "document_type": "slide|chart|financial_document|infographic|logo|other",
                "company_name": "",
                "sector": "",
                "stage": "",
                "revenue": null,
                "growth_rate": null,
                "team_size": null,
                "funding_raised": null,
                "funding_seeking": null,
                "market_size": null,
                "problem": "",
                "solution": "",
                "business_model": "",
                "traction_metrics": [],
                "founders": [],
                "competitors": [],
                "key_partnerships": [],
                "extracted_text": "all readable text from the image",
                "key_metrics": [
                    {"metric": "name", "value": "value", "unit": "unit if any"}
                ],
                "confidence_score": 0.0
            }
            
            Rules:
            - Only extract information explicitly visible in the image
            - Use null for missing numeric values, empty strings for missing text
            - Set confidence_score between 0.0-1.0 based on clarity of information
            - Include ALL readable text in extracted_text field
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
        {context_info}Extract structured business information from this {doc_type}. Be precise and only include information explicitly mentioned.

        Document text:
        {text}

        Return a JSON object with this exact structure:
        {{
            "company_name": "",
            "sector": "",
            "stage": "",
            "revenue": null,
            "growth_rate": null,
            "team_size": null,
            "funding_raised": null,
            "funding_seeking": null,
            "market_size": null,
            "problem": "",
            "solution": "",
            "business_model": "",
            "traction_metrics": [],
            "founders": [],
            "competitors": [],
            "key_partnerships": [],
            "confidence_score": 0.0
        }}

        Rules:
        - Use null for numbers not mentioned, empty strings for missing text
        - Arrays should contain specific items mentioned in the document
        - confidence_score: 0.0-1.0 based on information clarity
        - Only extract explicitly stated information
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

            # TODO: remove comments
            await asyncio.sleep(5)
            
            # response = await asyncio.to_thread(self.model.models.generate_content, model="gemini-2.5-flash", contents=[prompt])
            
            # if not response or not response.text:
            #     raise Exception("Empty synthesis response from Gemini")
            
            # # Parse synthesis result
            # response_text = response.text.strip()
            response_text = '```json\n{\n  "synthesized_data": {\n    "company_name": "Sia",\n    "sector": "AI and Data Analytics",\n    "stage": "Seed",\n    "geography": "Global (headquartered in Bengaluru, India)",\n    "founded": "2022",\n    "description": "Sia is an Agentic AI for Data Analytics developed by Datastride Analytics. It aims to democratize data analysis by providing a simple chat interface that brings a full data team experience to everyone in an organization. The product focuses on simplifying data analytics, reducing the cost of AI adoption, and unifying organizational data processes through features like recommender engines, auto visualizations, no-code model building, and unified data integration.",\n    "financials": {\n      "revenue": 400000.0,\n      "growth_rate": 0.43,\n      "burn_rate": 16867.0,\n      "funding_raised": 520964.0,\n      "funding_seeking": 602410.0,\n      "valuation": null,\n      "runway_months": 6\n    },\n    "market": {\n      "size": 300000000000.0,\n      "target_segment": "Medium to large enterprises (500+ employees, $5M+ revenue) handling large volumes of data and using legacy systems.",\n      "competitors": [\n        "Alteryx",\n        "Dataiku",\n        "Obviously.AI"\n      ],\n      "growth_rate": 0.43\n    },\n    "team": {\n      "size": null,\n      "founders": [\n        "Divya Krishna R",\n        "Sumalata Kamat",\n        "Karthik C"\n      ],\n      "key_personnel": []\n    },\n    "product": {\n      "name": "Sia",\n      "description": "Sia is an Agentic AI solution providing a generative AI-driven chat interface for data analytics. Key features include quick analytics widgets, instant data transformations, scalable data pipelines, custom code integration, feature readability, AI guidance, conversational AI, automated charts, AI deep thinking, and unified data integration from various sources. It uses a multi-agent architecture (swarm and solo agents) and supports flexible deployment (on-premise, hybrid, or cloud).",\n      "stage": "Early product deployment / early traction",\n      "business_model": "Subscription fees (monthly/annual), one-time setup/deployment fees for on-premise solutions, annual maintenance fees, and marketplace commissions from selling data-based solutions.",\n      "competitive_advantage": "Democratization of AI & Data through a simple chat interface, context-aware insights, minimized bottlenecks, high margins due to client bearing infrastructure costs, established product, readily deployable, strong partnerships, and low R&D costs."\n    },\n    "traction": {\n      "customers": 5,\n      "users": null,\n      "partnerships": [\n        "Microsoft for Startups",\n        "NSRCEL (IIMB)",\n        "Vetrina",\n        "Saudi Telecom",\n        "Sobha group",\n        "Accolade",\n        "HDFCergo",\n        "Pfizer",\n        "Maruti Suzuki",\n        "Tata Elxsi",\n        "PROPEL ATHON",\n        "Data Services",\n        "primeNumber",\n        "Bosch",\n        "RayRC"\n      ],\n      "key_metrics": [\n        {\n          "metric": "Booked Revenue",\n          "value": "400,000 USD"\n        },\n        {\n          "metric": "Sales Pipeline Value",\n          "value": "400,000 USD"\n        },\n        {\n          "metric": "Projected Growth Opportunities",\n          "value": "4,000,000 USD"\n        },\n        {\n          "metric": "Client Lifetime Value (LTV)",\n          "value": ">1,000,000 USD"\n        },\n        {\n          "metric": "LTV:CAC Ratio",\n          "value": "Minimum 10"\n        },\n        {\n          "metric": "Profit After Tax (PAT)",\n          "value": "Minimum 30%"\n        },\n        {\n          "metric": "Time to Insights reduction",\n          "value": "90%"\n        },\n        {\n          "metric": "Volume of Data Processed increase",\n          "value": "10x"\n        },\n        {\n          "metric": "Data Analytics Budget reduction",\n          "value": "4x"\n        },\n        {\n          "metric": "Project Deployment Time saved",\n          "value": "80%"\n        }\n      ]\n    }\n  },\n  "data_quality": {\n    "consistency_score": 0.95,\n    "completeness_score": 0.7,\n    "confidence_score": 0.9,\n    "inconsistencies": [\n      "Market size growth rate for \'Global Data Analytics\' is 13% CAGR on slide 9, but an external source mentioned in the textual document for \'Big Data Analytics Market\' is 13.5% CAGR to $725.93 Billion by 2031. The data from slide 9, which is more specific to the company\'s niche (\'Agentic AI market\'), has been prioritized."\n    ],\n    "missing_critical_data": [\n      "Valuation",\n      "Total team size",\n      "Number of active users",\n      "Specific Annual Recurring Revenue (ARR) or Monthly Recurring Revenue (MRR)"\n    ]\n  },\n  "source_summary": {\n    "documents_processed": 1,\n    "primary_sources": [\n      "PDF Document (15 slides + 9 textual pages)"\n    ],\n    "data_coverage": {\n      "company_name": "Explicit",\n      "sector": "Explicit",\n      "stage": "Explicit",\n      "geography": "Inferred/Explicit",\n      "founded": "Explicit",\n      "description": "Synthesized",\n      "financials.revenue": "Explicit (booked/current) and projected",\n      "financials.growth_rate": "Explicit (market)",\n      "financials.burn_rate": "Explicit",\n      "financials.funding_raised": "Explicit (multiple sources combined)",\n      "financials.funding_seeking": "Explicit",\n      "financials.valuation": "Missing",\n      "financials.runway_months": "Explicit",\n      "market.size": "Explicit (TAM/SOM)",\n      "market.target_segment": "Explicit",\n      "market.competitors": "Explicit",\n      "market.growth_rate": "Explicit",\n      "team.size": "Missing",\n      "team.founders": "Explicit",\n      "team.key_personnel": "Missing",\n      "product.name": "Explicit",\n      "product.description": "Synthesized",\n      "product.stage": "Explicit",\n      "product.business_model": "Explicit",\n      "product.competitive_advantage": "Synthesized/Explicit",\n      "traction.customers": "Explicit (count)",\n      "traction.users": "Missing",\n      "traction.partnerships": "Explicit",\n      "traction.key_metrics": "Explicit"\n    }\n  }\n}\n```'
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
