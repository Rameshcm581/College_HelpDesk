# backend/Services/HelpdeskService/resources/webScraperService.py
import asyncio
import ipaddress
import logging
import re
import socket
import urllib.parse
from typing import List, Optional, Tuple
from bs4 import BeautifulSoup
import httpx

from resources.errors import FileValidationError, SSRFValidationError
from resources.pdfService import ExtractedPage

logger = logging.getLogger(__name__)

# Blocked hostnames known for cloud metadata or local access
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
}

# Explicit cloud metadata IPs
BLOCKED_IP_STRINGS = {
    "169.254.169.254",  # AWS/GCP/Azure metadata service
    "169.254.170.2",    # AWS ECS task metadata
    "fd00:ec2::254",    # AWS IPv6 metadata
}


class WebScraperService:
    """Service for controlled, SSRF-defended website ingestion.
    Validates URL schemes, resolves IPs, blocks internal/loopback/cloud-metadata networks,
    follows redirects with re-validation, and extracts structured content.
    """

    def __init__(
        self,
        max_download_bytes: int = 5 * 1024 * 1024,  # 5 MB
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 10.0,
        max_redirects: int = 3,
    ):
        self.max_download_bytes = max_download_bytes
        self.connect_timeout_seconds = connect_timeout_seconds
        self.read_timeout_seconds = read_timeout_seconds
        self.max_redirects = max_redirects

    def validate_url_against_ssrf(self, target_url: str) -> urllib.parse.ParseResult:
        """Enforces scheme restrictions (http, https) and ensures target hostname does not
        resolve to private, loopback, multicast, or cloud-metadata IPs.
        Raises SSRFValidationError on violation.
        """
        try:
            parsed = urllib.parse.urlparse(target_url.strip())
        except Exception as exc:
            raise SSRFValidationError(f"Malformed URL: {str(exc)}")

        if parsed.scheme.lower() not in ("http", "https"):
            raise SSRFValidationError(
                f"Forbidden URL scheme '{parsed.scheme}'. Only 'http' and 'https' are permitted."
            )

        hostname = parsed.hostname
        if not hostname:
            raise SSRFValidationError("Target URL must contain a valid hostname.")

        hostname_lower = hostname.lower()
        if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".internal") or hostname_lower.endswith(".local"):
            raise SSRFValidationError(f"Forbidden destination host: '{hostname}' is not accessible.")

        port = parsed.port or (80 if parsed.scheme == "http" else 443)

        # Resolve all DNS records for hostname
        try:
            addr_info = socket.getaddrinfo(hostname, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise SSRFValidationError(f"DNS resolution failure for host '{hostname}': {str(exc)}")

        if not addr_info:
            raise SSRFValidationError(f"No IP addresses resolved for host '{hostname}'.")

        for entry in addr_info:
            sockaddr = entry[4]
            ip_str = sockaddr[0]

            if ip_str in BLOCKED_IP_STRINGS:
                raise SSRFValidationError(f"Access to cloud metadata IP '{ip_str}' is strictly blocked.")

            try:
                ip_obj = ipaddress.ip_address(ip_str)
            except ValueError:
                raise SSRFValidationError(f"Invalid resolved IP '{ip_str}'.")

            if (
                ip_obj.is_loopback
                or ip_obj.is_private
                or ip_obj.is_link_local
                or ip_obj.is_multicast
                or ip_obj.is_reserved
                or ip_obj.is_unspecified
            ):
                raise SSRFValidationError(
                    f"Forbidden destination: host '{hostname}' resolves to private/restricted IP '{ip_str}'."
                )

        return parsed

    async def fetch_url_content(self, initial_url: str) -> Tuple[str, str, bytes]:
        """Fetches URL content while strictly validating redirects against SSRF attacks.
        Returns (final_url, content_type, raw_body_bytes).
        """
        current_url = initial_url
        redirect_count = 0

        timeout = httpx.Timeout(
            connect=self.connect_timeout_seconds,
            read=self.read_timeout_seconds,
            write=5.0,
            pool=5.0,
        )

        headers = {
            "User-Agent": "CollegeHelpDeskBot/1.0 (+http://helpdesk.institution.edu/bot)",
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
        }

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            while redirect_count <= self.max_redirects:
                # Re-validate target URL on initial fetch and EVERY redirect hop
                self.validate_url_against_ssrf(current_url)

                try:
                    response = await client.get(current_url, headers=headers)
                except httpx.RequestError as exc:
                    raise SSRFValidationError(f"Failed to connect to target URL: {str(exc)}")

                # Check for HTTP redirect status codes
                if response.is_redirect:
                    redirect_count += 1
                    if redirect_count > self.max_redirects:
                        raise SSRFValidationError(
                            f"Exceeded maximum allowed redirect hops ({self.max_redirects})."
                        )
                    location = response.headers.get("Location")
                    if not location:
                        raise SSRFValidationError("Redirect response missing 'Location' header.")
                    current_url = urllib.parse.urljoin(current_url, location)
                    continue

                # Successful terminal response
                if response.status_code >= 400:
                    raise SSRFValidationError(
                        f"Target server responded with HTTP {response.status_code}."
                    )

                content_type = response.headers.get("content-type", "").lower()
                allowed_types = ("text/html", "application/xhtml+xml", "text/plain")
                if not any(t in content_type for t in allowed_types):
                    raise FileValidationError(
                        f"Unsupported content type '{content_type}'. Must be text/html or text/plain.",
                        status_code=400,
                    )

                # Read body while enforcing max size limit
                content_bytes = response.content
                if len(content_bytes) > self.max_download_bytes:
                    raise FileValidationError(
                        f"Downloaded content exceeds size limit of {self.max_download_bytes // (1024*1024)} MB.",
                        status_code=413,
                    )

                return current_url, content_type, content_bytes

        raise SSRFValidationError("Redirect loop or excessive redirects encountered.")

    def parse_web_content(self, html_bytes: bytes, source_url: str) -> Tuple[str, List[ExtractedPage]]:
        """Parses HTML into a title and structured ExtractedPage objects for chunking."""
        try:
            soup = BeautifulSoup(html_bytes, "html.parser")
        except Exception as exc:
            raise FileValidationError(f"Failed to parse HTML document: {str(exc)}", status_code=400)

        # Extract title
        title = "Website Documentation"
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.h1:
            title = soup.h1.get_text(strip=True)

        # Strip unneeded and non-content elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe", "svg", "button", "form"]):
            tag.decompose()

        # Extract body text
        body = soup.body or soup
        text = body.get_text(separator="\n\n", strip=True)
        # Clean multiple spaces and blank lines
        clean_text = re.sub(r'\n{3,}', '\n\n', text).strip()

        if not clean_text:
            raise FileValidationError("Web page contains no extractable text content.", status_code=400)

        # Break long web page into synthetic pages of ~1500 chars to fit chunking
        page_char_budget = 1500
        paragraphs = [p.strip() for p in clean_text.split('\n\n') if p.strip()]

        pages: List[ExtractedPage] = []
        cur_parts: List[str] = []
        cur_len = 0
        page_num = 1

        for para in paragraphs:
            if cur_len + len(para) <= page_char_budget:
                cur_parts.append(para)
                cur_len += len(para) + 2
            else:
                if cur_parts:
                    p_text = "\n\n".join(cur_parts)
                    pages.append(
                        ExtractedPage(
                            page_number=page_num,
                            text=p_text,
                            char_count=len(p_text),
                        )
                    )
                    page_num += 1
                cur_parts = [para]
                cur_len = len(para)

        if cur_parts:
            p_text = "\n\n".join(cur_parts)
            pages.append(
                ExtractedPage(
                    page_number=page_num,
                    text=p_text,
                    char_count=len(p_text),
                )
            )

        return title, pages


web_scraper_service = WebScraperService()
