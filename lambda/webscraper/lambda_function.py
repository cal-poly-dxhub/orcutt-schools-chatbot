#!/usr/bin/env python3
"""
Lambda Web Scraper for Orcutt Schools
Scrapes website content and saves to S3 for knowledge base ingestion
UPDATED: Excludes board agenda and minutes files from specific board trustee pages.
"""

import json
import boto3
import requests
from bs4 import BeautifulSoup
import re
import hashlib
import time
from urllib.parse import urljoin, urlparse, parse_qs
from collections import deque
from datetime import datetime
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from xml.etree import ElementTree as ET
from pypdf import PdfReader
import io

# Configure logging for Lambda (console only, no file uploads)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class LambdaWebScraper:
    def __init__(self, base_url, s3_bucket, max_workers=4, max_pages=200):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.s3_bucket = s3_bucket
        self.max_workers = max_workers
        self.max_pages = max_pages
        self.logger = logger
        
        # Initialize S3 client
        self.s3_client = boto3.client('s3')
        
        # Track visited URLs and downloaded files
        self.visited_urls = set()
        self.downloaded_files = set()
        self.agenda_files = []  # Track agenda files for date extraction
        self.excluded_files = []  # Track excluded board files
        
        # Thread-safe locks
        self.visited_lock = threading.Lock()
        self.downloaded_lock = threading.Lock()
        self.agenda_lock = threading.Lock()
        self.excluded_lock = threading.Lock()
        
        # File extensions to download (from original code)
        self.downloadable_extensions = {
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.txt', '.csv'
        }
        
        # File extensions to explicitly exclude (from original code)
        self.excluded_extensions = {
            '.css', '.js', '.ico', '.png', '.jpg', '.jpeg', '.gif',
            '.woff', '.woff2', '.ttf', '.eot', '.map', '.json'
        }

        # URL patterns to exclude (feeds, APIs, dynamic content)
        self.excluded_url_patterns = [
            r'pageID=smartSiteFeed',  # SmartSite RSS feeds
            r'pageID=.*Feed',         # Other feed types
            r'pageID=rss',           # RSS feeds
            r'pageID=json',          # JSON endpoints
            r'pageID=xml',           # XML endpoints
            r'pageID=api',           # API endpoints
            r'feed=.*%',             # URLs with encoded feed parameters
            r'articleID=\d+',        # Direct article IDs (often dynamic)
            r'ajax=.*',              # AJAX endpoints
            r'callback=.*',          # JSONP callbacks
            r'\.json\?',             # JSON endpoints with parameters
            r'\.xml\?',              # XML endpoints with parameters
            r'export=.*',            # Export functions
            r'print=.*',             # Print versions
        ]
        
        # NEW: Board trustee pages where we should exclude agenda/minutes files
        self.board_trustee_pages = {
            'https://www.orcuttschools.net/boardoftrustees',
            'https://www.orcuttschools.net/44037_3'
        }
        
        # Date patterns for agenda files (from original code)
        self.date_patterns = [
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'(?:meeting|agenda).*?(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'board\s+meeting.*?((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
        ]
    
    def create_session(self):
        """Create a new session for each thread."""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        return session
    
    def is_board_file_from_trustee_page(self, file_url, source_page_url):
        """Check if a file is a board agenda/minutes file from a board trustee page."""
        
        # More flexible URL matching - check if URL contains trustee page identifiers
        trustee_page_patterns = [
            'boardoftrustees',
            '44037_3',
            '33968_3',
            '34741_3',
            '33966_3',
            '34736_3',
            '47216_2'
        ]
        
        is_trustee_page = any(pattern in source_page_url.lower() for pattern in trustee_page_patterns)
        
        if not is_trustee_page:
            return False
        
        # Extract just the filename from the URL
        parsed_url = urlparse(file_url)
        filename = parsed_url.path.split('/')[-1].lower()
        
        # If no filename extracted, skip
        if not filename or not filename.endswith('.pdf'):
            return False
        
        # Enhanced patterns to catch board files
        board_patterns = [
            r'.*agenda.*\.pdf$',
            r'.*minutes.*\.pdf$',
            r'.*meeting.*\.pdf$',
            r'.*board.*\.pdf$',
            r'.*special.*\.pdf$',
            r'.*regular.*\.pdf$',
            r'.*public.*\.pdf$',
            r'.*charter.*\.pdf$'
        ]
        
        # Check patterns
        for pattern in board_patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                logger.info(f"Excluding board file: {filename} (pattern: {pattern})")
                with self.excluded_lock:
                    self.excluded_files.append({
                        'file_url': file_url,
                        'filename': filename,
                        'source_page': source_page_url,
                        'matched_pattern': pattern
                    })
                return True
        
        # Check keywords
        keywords = ['specialboard', 'publicagenda', 'boardagenda', 'boardminutes',
                    'meeting-materials', 'board-minutes', 'board-meeting', 'charter']
        
        for keyword in keywords:
            if keyword in filename:
                logger.info(f"Excluding board file: {filename} (keyword: {keyword})")
                with self.excluded_lock:
                    self.excluded_files.append({
                        'file_url': file_url,
                        'filename': filename,
                        'source_page': source_page_url,
                        'matched_pattern': f'keyword_{keyword}'
                    })
                return True
        
        return False
    
    def is_feed_or_dynamic_url(self, url):
        """Check if URL is a feed or dynamic content endpoint that should be excluded."""
        for pattern in self.excluded_url_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                logger.debug(f"Excluding feed/dynamic URL: {url} (matched pattern: {pattern})")
                return True
        
        # Additional check for complex query parameters that suggest dynamic content
        parsed = urlparse(url)
        if parsed.query:
            query_params = parse_qs(parsed.query)
            
            # Check for encoded JSON or complex data structures
            for param, values in query_params.items():
                for value in values:
                    if (len(value) > 100 or  # Very long parameter values
                        '%22' in value or    # Encoded quotes suggest JSON
                        '%7B' in value or    # Encoded { suggests JSON
                        '%5B' in value or    # Encoded [ suggests arrays
                        value.count('%') > 10):  # Heavily encoded content
                        logger.debug(f"Excluding complex parameter URL: {url}")
                        return True
        
        return False
    
    def is_valid_url(self, url):
        """Check if URL is valid and belongs to the target domain (from original code)."""
        try:
            if self.is_feed_or_dynamic_url(url):
                return False
            
            parsed = urlparse(url)
            
            # More comprehensive domain checking
            is_same_domain = (
                parsed.netloc == self.domain or 
                parsed.netloc == f"www.{self.domain}" or
                parsed.netloc == self.domain.replace('www.', '') or
                parsed.netloc.endswith(f".{self.domain.replace('www.', '')}")
            )
            
            is_valid_scheme = parsed.scheme in ['http', 'https']
            
            # Exclude problematic URLs
            is_excluded = any(exclude in url.lower() for exclude in [
                'mailto:', 'tel:', 'javascript:', '#', 'void(0)', 'data:'
            ])
            
            # Allow relative URLs and same-domain URLs
            is_relative = not parsed.netloc or is_same_domain
            
            return (is_valid_scheme or not parsed.scheme) and is_relative and not is_excluded
            
        except Exception as e:
            logger.debug(f"URL validation error for {url}: {str(e)}")
            return False
    
    def sanitize_filename(self, filename):
        """Sanitize filename for safe storage (from original code)."""
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = filename.strip('. ')
        return filename[:200]  # Limit length
    
    def get_url_hash(self, url):
        """Generate a short hash for the URL to use in filenames."""
        return hashlib.md5(url.encode()).hexdigest()[:8]
    
    def get_domain_prefix(self, url):
        """Extract short domain prefix (from original code)."""
        domain = urlparse(url).netloc
        if domain.startswith('www.'):
            return 'main'
        elif '.' in domain:
            return domain.split('.')[0]  # Gets 'lakeview', 'ojhs', etc.
        return 'main'
    
    def create_bedrock_metadata(self, original_url, filename, title="", content_type="text/plain", 
                               file_size=0, is_agenda=False, meeting_date=None, source_webpage_url=None):
        """Create AWS Bedrock-compatible metadata (from original code)."""
        
        # Determine document type
        file_ext = filename.split('.')[-1].lower() if '.' in filename else ''
        if file_ext == 'txt':
            doc_type = "webpage"
            doc_category = "web_content"
        elif file_ext == 'pdf':
            doc_type = "document"
            doc_category = "pdf_document"
        elif file_ext in ['doc', 'docx']:
            doc_type = "document"
            doc_category = "word_document"
        elif file_ext in ['xls', 'xlsx']:
            doc_type = "spreadsheet"
            doc_category = "excel_document"
        elif file_ext in ['ppt', 'pptx']:
            doc_type = "presentation"
            doc_category = "powerpoint_document"
        else:
            doc_type = "file"
            doc_category = "other_document"
        
        # Determine page type
        filename_lower = filename.lower()
        if 'index' in filename_lower or filename_lower.startswith('home'):
            page_type = "homepage"
        elif 'about' in filename_lower:
            page_type = "about"
        elif 'contact' in filename_lower:
            page_type = "contact"
        elif 'agenda' in filename_lower:
            page_type = "agenda"
        elif 'board' in filename_lower:
            page_type = "board"
        else:
            page_type = "content"
        
        # Create AWS Bedrock compatible metadata
        metadata = {
            "metadataAttributes": {
                "source": source_webpage_url or original_url,
                "file_url": original_url,
                "title": title or filename,
                "document_type": doc_type,
                "document_category": doc_category,
                "page_type": page_type,
                "file_extension": f".{file_ext}",
                "last_modified": datetime.now().strftime('%Y-%m-%d'),
                "content_type": content_type,
                "domain": urlparse(source_webpage_url or original_url).netloc,
            }
        }
        
        # Add file size if available
        if file_size > 0:
            metadata["metadataAttributes"]["file_size"] = int(file_size)
        
        # Add meeting date for agenda files
        if is_agenda and meeting_date:
            metadata["metadataAttributes"]["meeting_date"] = meeting_date
        
        return metadata
    
    def upload_to_s3(self, content, s3_key, content_type='application/octet-stream'):
        """Upload content directly to S3 bucket root (no folders)."""
        try:
            if isinstance(content, str):
                content = content.encode('utf-8')
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,  # Direct to bucket root, no prefix
                Body=content,
                ContentType=content_type
            )
            logger.info(f"Uploaded to S3: s3://{self.s3_bucket}/{s3_key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            return False
    
    def s3_file_exists(self, s3_key):
        """Check if file already exists in S3."""
        try:
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
            return True
        except:
            return False
    
    def download_from_s3(self, s3_key):
        """Download file content from S3."""
        try:
            response = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            return response['Body'].read()
        except:
            return None
    
    def get_s3_filename(self, url, filename, source_url=None):
        """Generate S3 filename with domain prefix (no folders)."""
        domain_prefix = self.get_domain_prefix(url)
        safe_filename = self.sanitize_filename(filename)
        return f"{domain_prefix}_{safe_filename}"
    
    def extract_text_content(self, soup):
        """Extract readable text content from BeautifulSoup object (from original code)."""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def extract_date_from_file_content(self, file_content, filename):
        """Extract meeting date from file content using pypdf."""
        try:
            if filename.lower().endswith('.pdf'):
                # Extract from PDF content using pypdf
                try:
                    pdf_file = io.BytesIO(file_content)
                    reader = PdfReader(pdf_file)
                    text = ""
                    max_pages = min(2, len(reader.pages))
                    for page_num in range(max_pages):
                        page_text = reader.pages[page_num].extract_text()
                        if page_text:
                            text += page_text
                except Exception as pdf_error:
                    logger.warning(f"Could not extract text from PDF {filename}: {pdf_error}")
                    return None
            else:
                # Extract from text file
                text = file_content.decode('utf-8', errors='ignore')[:1000]  # First 1000 chars
            
            # Search for dates (unchanged)
            for pattern in self.date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    date_str = matches[0] if isinstance(matches[0], str) else matches[0]
                    return self.normalize_date(date_str.strip())
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting date from {filename}: {str(e)}")
            return None
    
    def normalize_date(self, date_str):
        """Normalize date to YYYY-MM-DD format (from original code)."""
        try:
            formats = [
                '%B %d, %Y', '%B %d %Y', '%m/%d/%Y', 
                '%m-%d-%Y', '%Y-%m-%d', '%d/%m/%Y'
            ]
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            return date_str
        except:
            return date_str
    
    def file_already_exists(self, url, filename):
        """Check if file already exists to avoid re-downloading (from original code)."""
        s3_filename = self.get_s3_filename(url, filename)
        metadata_filename = f"{s3_filename}.metadata.json"
        
        if self.s3_file_exists(s3_filename) and self.s3_file_exists(metadata_filename):
            try:
                # Check if metadata contains the same file URL
                metadata_content = self.download_from_s3(metadata_filename)
                if metadata_content:
                    metadata = json.loads(metadata_content.decode('utf-8'))
                    meta_attrs = metadata.get('metadataAttributes', {})
                    if (meta_attrs.get('file_url') == url or 
                        meta_attrs.get('source') == url):
                        logger.info(f"File already exists, skipping: {filename}")
                        return True
            except Exception:
                pass
        return False
    
    def download_file(self, url, source_url):
        """Download a file and save to S3 with metadata (from original code)."""
        try:
            # NEW: Check if this is a board file from a trustee page and should be excluded
            if self.is_board_file_from_trustee_page(url, source_url):
                logger.info(f"Skipping board agenda/minutes file from trustee page: {url}")
                return True  # Return True to indicate "successful" handling (i.e., intentionally skipped)
            
            session = self.create_session()
            logger.info(f"Downloading file: {url}")
            response = session.get(url, timeout=30)
            response.raise_for_status()
            
            # Get filename from URL or Content-Disposition header
            filename = None
            if 'Content-Disposition' in response.headers:
                cd = response.headers['Content-Disposition']
                filename_match = re.search(r'filename="?([^"]+)"?', cd)
                if filename_match:
                    filename = filename_match.group(1)
            
            if not filename:
                filename = urlparse(url).path.split('/')[-1]
                if not filename or '.' not in filename:
                    content_type = response.headers.get('content-type', '').lower()
                    if 'pdf' in content_type:
                        ext = '.pdf'
                    else:
                        ext = '.bin'
                    filename = f"file_{self.get_url_hash(url)}{ext}"
            
            filename = self.sanitize_filename(filename)
            
            # Check if file already exists
            if self.file_already_exists(url, filename):
                with self.downloaded_lock:
                    self.downloaded_files.add(url)
                return True
            
            # Ensure unique filename
            counter = 1
            original_filename = filename
            s3_filename = self.get_s3_filename(url, filename)
            while self.s3_file_exists(s3_filename):
                name, ext = original_filename.rsplit('.', 1) if '.' in original_filename else (original_filename, '')
                filename = f"{name}_{counter}.{ext}" if ext else f"{name}_{counter}"
                s3_filename = self.get_s3_filename(url, filename)
                counter += 1
            
            # Upload file to S3
            content_type = response.headers.get('content-type', 'application/octet-stream')
            if self.upload_to_s3(response.content, s3_filename, content_type):
                
                # Create and upload metadata
                metadata = self.create_bedrock_metadata(
                    original_url=url,
                    filename=filename,
                    title=filename,
                    content_type=content_type,
                    file_size=len(response.content),
                    source_webpage_url=source_url
                )
                
                metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
                metadata_filename = f"{s3_filename}.metadata.json"
                self.upload_to_s3(metadata_json, metadata_filename, 'application/json')
                
                # Track agenda files for date extraction (only if not excluded)
                if 'agenda' in filename.lower():
                    with self.agenda_lock:
                        self.agenda_files.append((s3_filename, url, response.content))
                
                with self.downloaded_lock:
                    self.downloaded_files.add(url)
                
                logger.info(f"Successfully uploaded file: {filename}")
                return True
            
        except Exception as e:
            logger.error(f"Error downloading file {url}: {str(e)}")
        
        return False
    
    def webpage_already_exists(self, url):
        """Check if webpage already exists to avoid re-processing (from original code)."""
        # Create potential filename
        parsed_url = urlparse(url)
        path_parts = [part for part in parsed_url.path.split('/') if part]
        
        domain_prefix = self.get_domain_prefix(url)
        
        if path_parts:
            filename = f"{domain_prefix}_{'_'.join(path_parts)}"
        else:
            filename = f"{domain_prefix}_index"
        
        if parsed_url.query:
            filename += f"_query_{self.get_url_hash(parsed_url.query)}"
        
        filename = self.sanitize_filename(filename) + '.txt'
        metadata_filename = f"{filename}.metadata.json"
        
        if self.s3_file_exists(filename) and self.s3_file_exists(metadata_filename):
            try:
                metadata_content = self.download_from_s3(metadata_filename)
                if metadata_content:
                    metadata = json.loads(metadata_content.decode('utf-8'))
                    if metadata.get('metadataAttributes', {}).get('source') == url:
                        logger.info(f"Webpage already exists, skipping: {filename}")
                        return True
            except Exception:
                pass
        return False
    
    def save_webpage(self, url, soup, response_content):
        """Save webpage content as text file to S3 with metadata (from original code)."""
        try:
            # Check if webpage already exists
            if self.webpage_already_exists(url):
                return True
            
            # Create filename based on URL (from original code)
            parsed_url = urlparse(url)
            path_parts = [part for part in parsed_url.path.split('/') if part]
            
            domain_prefix = self.get_domain_prefix(url)
            
            if path_parts:
                filename = f"{domain_prefix}_{'_'.join(path_parts)}"
            else:
                filename = f"{domain_prefix}_index"
            
            if parsed_url.query:
                filename += f"_query_{self.get_url_hash(parsed_url.query)}"
            
            filename = self.sanitize_filename(filename) + '.txt'
            
            # Ensure unique filename
            counter = 1
            original_filename = filename
            while self.s3_file_exists(filename):
                name = original_filename.replace('.txt', '')
                filename = f"{name}_{counter}.txt"
                counter += 1
            
            # Extract and prepare text content
            text_content = self.extract_text_content(soup)
            title = soup.title.string if soup.title else filename
            
            # Create full text content
            full_content = f"URL: {url}\nTitle: {title}\n{'=' * 50}\n\n{text_content}"
            
            # Upload webpage to S3
            if self.upload_to_s3(full_content, filename, 'text/plain'):
                
                # Create and upload metadata
                metadata = self.create_bedrock_metadata(
                    original_url=url,
                    filename=filename,
                    title=title,
                    content_type="text/plain",
                    file_size=len(full_content.encode('utf-8')),
                    source_webpage_url=url
                )
                
                metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
                metadata_filename = f"{filename}.metadata.json"
                self.upload_to_s3(metadata_json, metadata_filename, 'application/json')
                
                # Track agenda files for date extraction
                if 'agenda' in filename.lower():
                    with self.agenda_lock:
                        self.agenda_files.append((filename, url, full_content.encode('utf-8')))
                
                logger.info(f"Saved webpage to S3: {filename}")
                return True
            
        except Exception as e:
            logger.error(f"Error saving webpage {url}: {str(e)}")
        
        return False
    
    def find_links_and_files(self, soup, base_url):
        """Extract all links and downloadable files from the page (from original code)."""
        links = set()
        files = set()
        all_found_links = []
        
        # Find all links in ALL tags, including navigation areas
        for tag in soup.find_all(['a', 'link', 'area']):
            href = tag.get('href')
            if href:
                all_found_links.append(href)
                full_url = urljoin(base_url, href)
                
                # Check if it's a downloadable file
                parsed = urlparse(full_url)
                path_lower = parsed.path.lower()
                
                is_downloadable = any(path_lower.endswith(ext) for ext in self.downloadable_extensions)
                is_excluded = any(path_lower.endswith(ext) for ext in self.excluded_extensions)
                
                is_file = is_downloadable and not is_excluded
                
                if is_file:
                    files.add(full_url)
                elif self.is_valid_url(full_url):
                    # Additional check: don't crawl excluded file types as webpages
                    is_excluded_type = any(path_lower.endswith(ext) for ext in self.excluded_extensions)
                    if not is_excluded_type:
                        links.add(full_url)
        
        # Also check for files in other tags (excluding images)
        for tag in soup.find_all(['embed', 'object', 'iframe']):
            src = tag.get('src') or tag.get('data')
            if src:
                full_url = urljoin(base_url, src)
                parsed = urlparse(full_url)
                path_lower = parsed.path.lower()
                
                is_downloadable = any(path_lower.endswith(ext) for ext in self.downloadable_extensions)
                is_excluded = any(path_lower.endswith(ext) for ext in self.excluded_extensions)
                
                if is_downloadable and not is_excluded:
                    files.add(full_url)
        
        # Look for data attributes that might contain URLs
        for tag in soup.find_all(attrs={'data-href': True}):
            href = tag.get('data-href')
            if href:
                full_url = urljoin(base_url, href)
                if self.is_valid_url(full_url):
                    links.add(full_url)
        
        # Enhanced debugging: Log link discovery details
        logger.debug(f"Found {len(all_found_links)} raw links on {base_url}")
        logger.debug(f"Valid internal links: {len(links)}, Files: {len(files)}")
        
        return links, files
    
    def process_agenda_dates(self):
        """Extract dates from agenda files and update metadata (from original code)."""
        if not self.agenda_files:
            return
            
        logger.info(f"Processing {len(self.agenda_files)} agenda files for date extraction...")
        
        for s3_filename, original_url, file_content in self.agenda_files:
            try:
                # Extract date
                meeting_date = self.extract_date_from_file_content(file_content, s3_filename)
                
                if meeting_date:
                    # Update metadata file
                    metadata_filename = f"{s3_filename}.metadata.json"
                    
                    if self.s3_file_exists(metadata_filename):
                        metadata_content = self.download_from_s3(metadata_filename)
                        if metadata_content:
                            metadata = json.loads(metadata_content.decode('utf-8'))
                            
                            metadata['metadataAttributes']['meeting_date'] = meeting_date
                            
                            metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
                            self.upload_to_s3(metadata_json, metadata_filename, 'application/json')
                            
                            logger.info(f"Added meeting date {meeting_date} to {s3_filename}")
                    else:
                        logger.warning(f"Metadata file not found for {s3_filename}")
                else:
                    logger.warning(f"No date found in {s3_filename}")
                    
            except Exception as e:
                logger.error(f"Error processing agenda date for {s3_filename}: {str(e)}")
    
    def fetch_sitemap_urls(self):
        """Fetch URLs from sitemap.xml if it exists (from original code)."""
        sitemap_urls = set()
        
        sitemap_locations = ['/sitemap.xml', '/sitemap_index.xml', '/sitemap.xml.gz']
        
        for sitemap_path in sitemap_locations:
            sitemap_url = urljoin(self.base_url, sitemap_path)
            
            try:
                session = self.create_session()
                logger.info(f"Checking for sitemap: {sitemap_url}")
                response = session.get(sitemap_url, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"Found sitemap: {sitemap_url}")
                    
                    try:
                        root = ET.fromstring(response.content)
                        
                        # Standard sitemap
                        for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                            loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                            if loc_elem is not None and loc_elem.text:
                                url = loc_elem.text.strip()
                                if self.is_valid_url(url):
                                    sitemap_urls.add(url)
                        
                        # Sitemap index
                        for sitemap_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                            loc_elem = sitemap_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                            if loc_elem is not None and loc_elem.text:
                                sub_sitemap_url = loc_elem.text.strip()
                                sub_urls = self.fetch_sub_sitemap(sub_sitemap_url)
                                sitemap_urls.update(sub_urls)
                        
                        logger.info(f"Found {len(sitemap_urls)} URLs in sitemap: {sitemap_url}")
                        break
                        
                    except ET.ParseError as e:
                        logger.warning(f"Could not parse sitemap XML {sitemap_url}: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.debug(f"Sitemap not found or error accessing {sitemap_url}: {str(e)}")
                continue
        
        if sitemap_urls:
            logger.info(f"Total URLs found in sitemaps: {len(sitemap_urls)}")
        else:
            logger.info("No sitemaps found or no valid URLs in sitemaps")
        
        return sitemap_urls
    
    def fetch_sub_sitemap(self, sitemap_url):
        """Fetch URLs from a sub-sitemap (from original code)."""
        urls = set()
        try:
            session = self.create_session()
            response = session.get(sitemap_url, timeout=30)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                
                for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc_elem is not None and loc_elem.text:
                        url = loc_elem.text.strip()
                        if self.is_valid_url(url):
                            urls.add(url)
                            
        except Exception as e:
            logger.warning(f"Error fetching sub-sitemap {sitemap_url}: {str(e)}")
        
        return urls
    
    def process_url(self, url):
        """Process a single URL - to be used with threading (from original code)."""
        try:
            session = self.create_session()
            logger.info(f"Crawling: {url}")
            response = session.get(url, timeout=30, allow_redirects=True)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Save webpage to S3
            self.save_webpage(url, soup, response.content)
            
            # Find links and files with enhanced discovery
            links, files = self.find_links_and_files(soup, url)
            
            # Additional link discovery: Look for links in text content
            text_content = soup.get_text()
            url_patterns = re.findall(r'https?://[^\s<>"]+|/[a-zA-Z0-9\-_./]+', text_content)
            for pattern in url_patterns:
                if pattern.startswith('/'):
                    potential_url = urljoin(url, pattern)
                    if self.is_valid_url(potential_url) and potential_url not in links:
                        links.add(potential_url)
                        logger.debug(f"Found additional URL in text: {potential_url}")
            
            # Log comprehensive discovery results
            logger.debug(f"Discovery summary for {url}: {len(links)} links, {len(files)} files")
            
            return links, files, url
            
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}")
            return set(), set(), url
    
    def download_files_threaded(self, file_urls_with_source):
        """Download files using threading (from original code)."""
        if not file_urls_with_source:
            return
            
        logger.info(f"Starting threaded download of {len(file_urls_with_source)} files...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit download tasks
            future_to_url = {
                executor.submit(self.download_file, file_url, source_url): (file_url, source_url)
                for file_url, source_url in file_urls_with_source
                if file_url not in self.downloaded_files
            }
            
            # Process completed downloads
            for future in as_completed(future_to_url):
                file_url, source_url = future_to_url[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Download failed for {file_url}: {str(e)}")
    
    def crawl_website(self):
        """Main crawling function with threading support (from original code)."""
        logger.info(f"Starting to crawl: {self.base_url}")
        
        # Queue for URLs to visit - start with base URL and sitemap URLs
        url_queue = deque([self.base_url])
        
        # Add sitemap URLs to the queue
        sitemap_urls = self.fetch_sitemap_urls()
        for url in sitemap_urls:
            if url not in self.visited_urls:
                url_queue.append(url)
        
        logger.info(f"Starting crawl with {len(url_queue)} URLs (including {len(sitemap_urls)} from sitemap)")
        all_files_to_download = []
        
        # Track crawling statistics
        pages_processed = 0
        total_links_found = 0
        
        while url_queue and pages_processed < self.max_pages:
            # Process URLs in batches
            current_batch = []
            batch_size = min(self.max_workers, len(url_queue))
            
            for _ in range(batch_size):
                if url_queue:
                    url = url_queue.popleft()
                    with self.visited_lock:
                        if url not in self.visited_urls:
                            current_batch.append(url)
                            self.visited_urls.add(url)
            
            if not current_batch:
                break
            
            # Process batch of URLs with threading
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_url = {
                    executor.submit(self.process_url, url): url 
                    for url in current_batch
                }
                
                batch_files = []
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        links, files, processed_url = future.result()
                        pages_processed += 1
                        total_links_found += len(links)
                        
                        # Add files to download list
                        for file_url in files:
                            batch_files.append((file_url, processed_url))
                        
                        # Add new links to queue with better deduplication
                        new_links_added = 0
                        for link in links:
                            with self.visited_lock:
                                if link not in self.visited_urls:
                                    url_queue.append(link)
                                    new_links_added += 1
                        
                        if new_links_added > 0:
                            logger.debug(f"Added {new_links_added} new links from {processed_url}")
                                    
                    except Exception as e:
                        logger.error(f"Error processing results for {url}: {str(e)}")
                
                # Download files from this batch
                if batch_files:
                    self.download_files_threaded(batch_files)
                    all_files_to_download.extend(batch_files)
                
                # Log progress periodically
                if pages_processed % 10 == 0:
                    logger.info(f"Progress: {pages_processed} pages processed, {len(url_queue)} in queue, {total_links_found} total links found")
        
        # Process agenda dates after all crawling is complete
        self.process_agenda_dates()
        
        logger.info(f"Crawling completed. Visited {len(self.visited_urls)} pages, downloaded {len(self.downloaded_files)} files.")
        logger.info(f"Excluded {len(self.excluded_files)} board files from trustee pages.")
        logger.info(f"Final statistics: {total_links_found} total links discovered across all pages.")

def lambda_handler(event, context):
    """Lambda function handler."""
    try:
        # Get parameters from event
        base_url = event.get('base_url')
        s3_bucket = event.get('s3_bucket')
        max_workers = event.get('max_workers', 4)
        max_pages = event.get('max_pages', 200)
        
        if not base_url or not s3_bucket:
            return {
                'statusCode': 400,
                'body': json.dumps('Missing required parameters: base_url and s3_bucket')
            }
        
        # Create scraper and start crawling
        scraper = LambdaWebScraper(base_url, s3_bucket, max_workers, max_pages)
        scraper.crawl_website()
        
        # Return results
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Scraping completed successfully',
                'base_url': base_url,
                'pages_crawled': len(scraper.visited_urls),
                'files_downloaded': len(scraper.downloaded_files),
                'board_files_excluded': len(scraper.excluded_files),
                's3_bucket': s3_bucket,
                'agenda_files_processed': len(scraper.agenda_files),
                'files_saved_to_bucket_root': True,
                'meeting_dates_extracted': True,
                'board_file_exclusion_enabled': True
            })
        }
        
    except Exception as e:
        logger.error(f"Lambda function error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }
