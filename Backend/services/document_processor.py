# services/document_processor.py
import asyncio
import tempfile
import aiohttp
import os
from typing import List, Dict
import google.generativeai as genai
from PyPDF2 import PdfReader
from PIL import Image
from pptx import Presentation
import json
import logging
from datetime import timedelta
from io import BytesIO
from utils.ai_client import configure_gemini
from models.database import get_storage_bucket

logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        """Initialize the document processor with Gemini multimodal support"""
        
        # Initialize Gemini API
        self.gemini_available = configure_gemini()
        if self.gemini_available:
            self.model = genai.GenerativeModel('gemini-1.5-pro')
            logger.info("DocumentProcessor initialized with Gemini multimodal support")
        else:
            logger.warning("Gemini not available - using basic text processing only")
            self.model = None
        
        # File type classifications
        self.image_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.gif'}
        self.office_formats = {'.pptx', '.ppt', '.docx', '.doc'}
        self.pdf_formats = {'.pdf'}
        self.text_formats = {'.txt', '.md', '.json', '.csv', '.xml', '.html'}

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

    async def process_documents_from_storage(self, storage_paths: List[str]) -> Dict:
        """Process documents from Firebase Storage paths"""
        
        if not storage_paths:
            return {'error': 'No storage paths provided'}

        # Convert storage paths to download URLs
        download_urls = await self.generate_download_urls(storage_paths)

        if not download_urls:
            return {'error': 'No valid files found at provided storage paths'}

        # Extract just the URLs for processing
        file_urls = list(download_urls.values())
        
        tasks = []
        for file_name, file_url in download_urls.items():
            task = asyncio.create_task(self.process_single_document(file_name, file_url))
            tasks.append(task)
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error processing documents: {e}")
            return {'error': f'Document processing failed: {str(e)}'}
        
        # Filter successful results
        processed_docs = []
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                errors.append({
                    'file_url': file_urls[i],
                    'error': str(result)
                })
            else:
                processed_docs.append({
                    'file_url': file_urls[i],
                    'extracted_data': result
                })
        
        if not processed_docs:
            return {
                'error': 'No documents were successfully processed',
                'errors': errors
            }
        
        # Synthesize all documents with Gemini
        try:
            synthesized = await self.synthesize_documents(processed_docs)
            synthesized['processing_errors'] = errors  # Include any individual errors
            return synthesized
        except Exception as e:
            logger.error(f"Document synthesis failed: {e}")
            return {
                'error': f'Document synthesis failed: {str(e)}',
                'individual_results': processed_docs,
                'processing_errors': errors
            }

    async def process_single_document(self, file_name: str,  file_url: str) -> Dict:
        """Enhanced document processing with Gemini multimodal support"""
        
        try:
            # Download file
            file_content = await self.download_file(file_url)
            file_extension = self._get_file_extension(file_name)
            
            logger.info(f"Processing {file_url} with extension {file_extension}")
            
            if not self.gemini_available:
                return await self._fallback_processing(file_content, file_url, file_extension)
            
            # Route to appropriate Gemini processor based on file type
            if file_extension in self.image_formats:
                return await self._process_image_with_gemini(file_content, file_url)
            
            elif file_extension in self.pdf_formats:
                return await self._process_pdf_enhanced(file_content, file_url)
            
            elif file_extension in self.office_formats:
                return await self._process_office_document(file_content, file_url, file_extension)
            
            elif file_extension in self.text_formats:
                return await self._process_text_with_gemini(file_content.decode('utf-8'), file_url)
            
            else:
                # Try intelligent fallback for unknown file types
                return await self._process_unknown_file(file_content, file_url)
        
        except Exception as e:
            logger.error(f"Error processing document {file_url}: {e}")
            return {
                'error': f'Document processing failed: {str(e)}',
                'text': '',
                'file_url': file_url
            }

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
        """Enhanced PDF processing with fallback to Gemini for image-based PDFs"""
        
        try:
            # First attempt: Extract text normally
            text_content, page_count = await self._extract_pdf_text(file_content)
            
            if text_content.strip():
                # Process extracted text with Gemini
                return await self._process_text_with_gemini(
                    text_content, 
                    file_url, 
                    extra_context=f"This is a PDF document with {page_count} pages"
                )
            
            # If no text found, try to process first few pages as images with Gemini
            logger.info(f"No text found in PDF {file_url}, attempting image-based processing...")
            return await self._process_pdf_as_images(file_content, file_url)
            
        except Exception as e:
            logger.error(f"PDF processing error for {file_url}: {e}")
            return {
                'error': f'PDF processing failed: {str(e)}',
                'file_url': file_url,
                'file_type': 'pdf'
            }

    async def _process_office_document(self, file_content: bytes, file_url: str, file_extension: str) -> Dict:
        """Process PowerPoint and Word documents"""
        
        try:
            if file_extension in {'.pptx', '.ppt'}:
                return await self._process_powerpoint(file_content, file_url)
            elif file_extension in {'.docx', '.doc'}:
                # For now, return error for Word docs (would need python-docx)
                return {
                    'error': 'Word document processing not yet implemented',
                    'suggestion': 'Please convert to PDF or text format',
                    'file_url': file_url,
                    'file_type': 'word_document'
                }
            else:
                return {
                    'error': f'Unsupported office format: {file_extension}',
                    'file_url': file_url
                }
                
        except Exception as e:
            logger.error(f"Office document processing error for {file_url}: {e}")
            return {
                'error': f'Office document processing failed: {str(e)}',
                'file_url': file_url
            }

    async def _process_powerpoint(self, file_content: bytes, file_url: str) -> Dict:
        """Process PowerPoint presentations"""
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pptx') as tmp_file:
                tmp_file.write(file_content)
                tmp_file.flush()
                
                # Extract text from slides
                presentation = Presentation(tmp_file.name)
                slide_contents = []
                
                for slide_num, slide in enumerate(presentation.slides):
                    slide_texts = []
                    
                    for shape in slide.shapes:
                        if hasattr(shape, 'text') and shape.text.strip():
                            slide_texts.append(shape.text.strip())
                    
                    if slide_texts:
                        slide_content = f"=== Slide {slide_num + 1} ===\n" + "\n".join(slide_texts)
                        slide_contents.append(slide_content)
                
                os.unlink(tmp_file.name)
                
                if slide_contents:
                    full_presentation_text = "\n\n".join(slide_contents)
                    return await self._process_text_with_gemini(
                        full_presentation_text,
                        file_url,
                        extra_context=f"This is a PowerPoint presentation with {len(slide_contents)} slides"
                    )
                else:
                    return {
                        'error': 'No text content found in PowerPoint slides',
                        'file_url': file_url,
                        'file_type': 'powerpoint'
                    }
                    
        except Exception as e:
            logger.error(f"PowerPoint processing error: {e}")
            return {
                'error': f'PowerPoint processing failed: {str(e)}',
                'file_url': file_url,
                'file_type': 'powerpoint'
            }

    async def _process_text_with_gemini(self, text_content: str, file_url: str, extra_context: str = "") -> Dict:
        """Process text content with Gemini for enhanced structured extraction"""
        
        if not text_content.strip():
            return {'error': 'Empty text content', 'text': '', 'file_url': file_url}
        
        try:
            return await self.extract_structured_data(text_content, 'business_document', extra_context)
        except Exception as e:
            return {
                'error': f'Text processing failed: {str(e)}',
                'raw_text': text_content[:1000] + "..." if len(text_content) > 1000 else text_content,
                'file_url': file_url
            }

    async def _process_unknown_file(self, file_content: bytes, file_url: str) -> Dict:
        """Intelligent fallback processing for unknown file types"""
        
        # Try as image first (Gemini can handle many image formats)
        try:
            return await self._process_image_with_gemini(file_content, file_url)
        except Exception:
            pass
        
        # Try as text
        try:
            text_content = file_content.decode('utf-8')
            return await self._process_text_with_gemini(text_content, file_url)
        except UnicodeDecodeError:
            pass
        
        # Try as PDF
        try:
            return await self._process_pdf_enhanced(file_content, file_url)
        except Exception:
            pass
        
        return {
            'error': 'Unable to process file with any available method',
            'file_url': file_url,
            'file_type': 'unknown'
        }

    async def _extract_pdf_text(self, file_content: bytes) -> tuple[str, int]:
        """Extract text from PDF and return text + page count"""
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file.flush()
            
            try:
                reader = PdfReader(tmp_file.name)
                text_parts = []
                page_count = len(reader.pages)
                
                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num + 1}: {e}")
                
                full_text = "\n\n".join(text_parts)
                
            finally:
                os.unlink(tmp_file.name)
            
            return full_text, page_count

    async def _process_pdf_as_images(self, file_content: bytes, file_url: str) -> Dict:
        """Process image-based PDF by converting pages to images (requires additional setup)"""
        
        # For now, return a helpful error message
        # To implement this, you'd need pdf2image: pip install pdf2image
        # and system dependencies: apt-get install poppler-utils
        
        return {
            'error': 'PDF appears to contain only images. Image-based PDF processing not yet implemented.',
            'suggestion': 'Consider using OCR software to convert to searchable PDF, or extract images manually.',
            'file_url': file_url,
            'file_type': 'image_based_pdf'
        }

    async def _fallback_processing(self, file_content: bytes, file_url: str, file_extension: str) -> Dict:
        """Basic fallback when Gemini is not available"""
        
        if file_extension in self.text_formats:
            try:
                text_content = file_content.decode('utf-8')
                return {
                    'company_name': "",
                    'sector': "",
                    'stage': "",
                    'revenue': None,
                    'growth_rate': None,
                    'team_size': None,
                    'funding_raised': None,
                    'funding_seeking': None,
                    'market_size': None,
                    'problem': "",
                    'solution': "",
                    'business_model': "",
                    'traction_metrics': [],
                    'founders': [],
                    'competitors': [],
                    'key_partnerships': [],
                    'confidence_score': 0.1,
                    'raw_text': text_content,
                    'extraction_method': 'fallback_text_only',
                    'file_url': file_url,
                    'note': 'Basic text extraction - Gemini not available for structured analysis'
                }
            except UnicodeDecodeError:
                return {'error': 'Cannot decode text file without Gemini', 'file_url': file_url}
        
        elif file_extension in self.pdf_formats:
            try:
                text_content, _ = await self._extract_pdf_text(file_content)
                if text_content:
                    return {
                        'raw_text': text_content,
                        'extraction_method': 'basic_pdf_text',
                        'file_url': file_url,
                        'note': 'Basic PDF text extraction - Gemini not available for structured analysis'
                    }
            except Exception:
                pass
        
        return {
            'error': 'Gemini not available and file type requires AI processing',
            'file_url': file_url,
            'suggestion': 'Configure Gemini API for advanced document processing'
        }

    def _parse_gemini_json_response(self, response_text: str) -> Dict:
        """Parse JSON from Gemini response with error handling"""
        try:
            # Find JSON in response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                parsed_data = json.loads(json_str)
                
                # Ensure required fields exist with defaults
                default_structure = {
                    'company_name': '',
                    'sector': '',
                    'stage': '',
                    'revenue': None,
                    'growth_rate': None,
                    'team_size': None,
                    'funding_raised': None,
                    'funding_seeking': None,
                    'market_size': None,
                    'problem': '',
                    'solution': '',
                    'business_model': '',
                    'traction_metrics': [],
                    'founders': [],
                    'competitors': [],
                    'key_partnerships': [],
                    'confidence_score': 0.5
                }
                
                # Merge with defaults
                for key, default_value in default_structure.items():
                    if key not in parsed_data:
                        parsed_data[key] = default_value
                
                return parsed_data
            else:
                return {
                    'error': 'Could not parse structured data from response',
                    'raw_response': response_text[:500] + "..." if len(response_text) > 500 else response_text
                }
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            return {
                'error': f'JSON parsing failed: {str(e)}',
                'raw_response': response_text[:500] + "..." if len(response_text) > 500 else response_text
            }

    def _get_file_extension(self, file_url: str) -> str:
        """Extract file extension from URL"""
        return os.path.splitext(file_url.lower())[1]

    # Legacy methods - maintaining backward compatibility
    async def process_pdf(self, file_content: bytes) -> Dict:
        """Legacy method - redirects to enhanced processing"""
        return await self._process_pdf_enhanced(file_content, "legacy_pdf_call")

    async def process_text(self, text_content: str) -> Dict:
        """Legacy method - redirects to enhanced processing"""
        return await self._process_text_with_gemini(text_content, "legacy_text_call")

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

    async def synthesize_documents(self, processed_docs: List[Dict]) -> Dict:
        """Enhanced document synthesis using Gemini"""
        
        if not processed_docs:
            return {'error': 'No processed documents to synthesize'}
        
        # Filter valid documents
        valid_docs = []
        doc_errors = []
        
        for doc in processed_docs:
            extracted_data = doc.get('extracted_data', {})
            if 'error' not in extracted_data:
                valid_docs.append(doc)
            else:
                doc_errors.append({
                    'file_url': doc.get('file_url', 'unknown'),
                    'error': extracted_data.get('error', 'Unknown error')
                })
        
        if not valid_docs:
            return {
                'error': 'No valid documents to synthesize',
                'document_errors': doc_errors
            }
        
        all_data = [doc['extracted_data'] for doc in valid_docs]
        
        # Create synthesis prompt
        data_str = json.dumps(all_data, indent=2)
        max_chars = 10000
        if len(data_str) > max_chars:
            data_str = data_str[:max_chars] + "\n... [data truncated for processing]"
        
        prompt = f"""
        Synthesize data from {len(all_data)} business documents. Cross-reference information and create a unified view.

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
                "documents_processed": {len(valid_docs)},
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
            
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            
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
                'documents_processed': len(valid_docs),
                'document_errors': doc_errors,
                'synthesis_method': 'gemini_enhanced'
            }
            
            return synthesis_result
            
        except json.JSONDecodeError as e:
            logger.error(f"Synthesis JSON parsing error: {e}")
            return {
                'error': f'Synthesis parsing failed: {str(e)}',
                'individual_results': all_data,
                'document_errors': doc_errors
            }
        except Exception as e:
            logger.error(f"Document synthesis failed: {e}")
            return {
                'error': f'Document synthesis failed: {str(e)}',
                'individual_results': all_data,
                'document_errors': doc_errors
            }