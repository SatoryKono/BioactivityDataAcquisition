#!/usr/bin/env python3
"""
BioETL Link Checker Plugin for MkDocs

This plugin validates all links in the documentation during the build process
and exposes the results as published link health metrics.

Issue #3094: Expose Link-Check Results as Published
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from mkdocs.plugins import BasePlugin

# Configure logging
log = logging.getLogger("mkdocs.plugins.link_checker")


class LinkCheckerPlugin(BasePlugin):
    """
    MkDocs plugin that checks all links in documentation and exposes results.

    Configuration:
    - enabled: Enable/disable the plugin (default: True)
    - timeout: HTTP request timeout in seconds (default: 10)
    - max_redirects: Maximum number of redirects to follow (default: 5)
    - ignore_patterns: List of patterns to ignore (default: ["localhost", "127.0.0.1"])
    - report_dir: Directory to save reports (default: "reports/links")
    - fail_on_error: Fail build if broken links found (default: False)
    """

    config_scheme = (
        ("enabled", lambda x: bool(x)),
        ("timeout", lambda x: int(x)),
        ("max_redirects", lambda x: int(x)),
        ("ignore_patterns", lambda x: x if isinstance(x, list) else [x]),
        ("report_dir", lambda x: str(x)),
        ("fail_on_error", lambda x: bool(x)),
    )

    def __init__(self):
        self.links_checked = 0
        self.valid_links = 0
        self.broken_links = 0
        self.redirect_links = 0
        self.link_results = []
        self.start_time = 0
        self.end_time = 0

    def on_startup(self, _command, _dirty):
        """Initialize plugin when MkDocs starts."""
        if not self.config["enabled"]:
            log.info("Link checker plugin is disabled")
            return

        log.info("Link checker plugin initialized")
        self.start_time = time.time()

    def on_post_build(self, config, **_kwargs):
        """Check all links after documentation build is complete."""
        if not self.config["enabled"]:
            return

        log.info("Starting link checking process...")
        site_dir = config["site_dir"]

        # Find all HTML files in the built site
        html_files = self._find_html_files(site_dir)
        log.info(f"Found {len(html_files)} HTML files to check")

        # Check all links in parallel
        self._check_links_in_files(html_files, site_dir)

        # Generate reports
        self._generate_reports(site_dir)

        # Log summary
        self._log_summary()

        # Fail build if configured and broken links found
        if self.config["fail_on_error"] and self.broken_links > 0:
            raise SystemExit(
                f"Link checking failed: {self.broken_links} broken links found"
            )

    def _find_html_files(self, site_dir: str) -> list[str]:
        """Find all HTML files in the built site directory."""
        return [str(path) for path in Path(site_dir).rglob("*.html")]

    def _check_links_in_files(self, html_files: list[str], site_dir: str):
        """Check all links in HTML files using thread pool for parallel processing."""
        base_url = f"file://{site_dir}/"

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []

            for html_file in html_files:
                relative_path = str(Path(html_file).relative_to(Path(site_dir)))
                futures.append(
                    executor.submit(
                        self._check_links_in_file, html_file, base_url, relative_path
                    )
                )

            # Process results as they complete
            for future in as_completed(futures):
                file_results = future.result()
                self.link_results.extend(file_results)

    def _check_links_in_file(
        self, html_file: str, _base_url: str, relative_path: str
    ) -> list[dict]:
        """Check all links in a single HTML file."""
        file_results = []

        try:
            with Path(html_file).open(encoding="utf-8") as f:
                content = f.read()

            soup = BeautifulSoup(content, "html.parser")

            # Check all anchor tags
            for anchor in soup.find_all("a", href=True):
                href = anchor["href"]
                text = anchor.get_text(strip=True) or "[no text]"

                result = self._check_link(href, text, relative_path, html_file)
                if result:
                    file_results.append(result)

                    # Update counters
                    if result["status"] == "valid":
                        self.valid_links += 1
                    elif result["status"] == "broken":
                        self.broken_links += 1
                    elif result["status"] == "redirect":
                        self.redirect_links += 1

                    self.links_checked += 1

        except Exception as e:
            log.error(f"Error checking links in {relative_path}: {e}")

        return file_results

    def _check_link(
        self, href: str, text: str, source_file: str, source_path: str
    ) -> dict | None:
        """Check a single link and return validation result."""
        # Skip empty or javascript links
        if (
            not href
            or href.startswith("javascript:")
            or href.startswith("mailto:")
            or href.startswith("tel:")
        ):
            return None

        # Skip ignored patterns
        if any(pattern in href for pattern in self.config["ignore_patterns"]):
            log.debug(f"Skipping ignored link: {href}")
            return None

        # Relative HTML links like "target.html" are internal too.
        parsed_href = urlparse(href)
        is_internal = not (parsed_href.scheme or parsed_href.netloc)

        result = {
            "source_file": source_file,
            "source_path": source_path,
            "link_url": href,
            "link_text": text,
            "status": "unknown",
            "http_code": None,
            "redirect_chain": [],
            "is_internal": is_internal,
            "error": None,
        }

        try:
            if is_internal:
                # For internal links, just check if file exists
                # Remove anchor part
                clean_href = href.split("#")[0]
                if clean_href.endswith(".html"):
                    # Check if HTML file exists
                    target_path = Path(source_path).parent / clean_href.lstrip("/")
                    if target_path.exists():
                        result["status"] = "valid"
                    else:
                        result["status"] = "broken"
                        result["error"] = "File not found"
                else:
                    # For non-HTML internal links, assume valid
                    result["status"] = "valid"
            else:
                # For external links, check HTTP status
                result.update(self._check_external_link(href))

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            log.error(f"Error checking link {href}: {e}")

        return result

    def _check_external_link(self, url: str) -> dict:
        """Check external link by making HTTP request."""
        result = {"http_code": None, "redirect_chain": [], "error": None}

        try:
            session = requests.Session()
            session.max_redirects = self.config["max_redirects"]

            response = session.get(
                url,
                timeout=self.config["timeout"],
                allow_redirects=True,
                headers={"User-Agent": "BioETL-LinkChecker/1.0"},
            )

            result["http_code"] = response.status_code

            # Check if redirect occurred
            if len(response.history) > 0:
                result["redirect_chain"] = [
                    {"url": r.url, "status": r.status_code} for r in response.history
                ]
                result["status"] = "redirect"
            elif 200 <= response.status_code < 400:
                result["status"] = "valid"
            else:
                result["status"] = "broken"

        except requests.exceptions.RequestException as e:
            result["status"] = "broken"
            result["error"] = str(e)

        return result

    def _generate_reports(self, site_dir: str):
        """Generate link check reports in various formats."""
        report_dir = Path(site_dir) / self.config["report_dir"]
        report_dir.mkdir(parents=True, exist_ok=True)

        # Generate JSON report
        json_report = self._generate_json_report()
        json_path = report_dir / "link-health.json"
        with json_path.open("w", encoding="utf-8") as f:
            import json

            json.dump(json_report, f, indent=2)

        # Generate HTML report
        html_report = self._generate_html_report()
        html_path = report_dir / "link-health.html"
        with html_path.open("w", encoding="utf-8") as f:
            f.write(html_report)

        # Generate badge
        badge = self._generate_badge()
        badge_path = report_dir / "link-badge.svg"
        with badge_path.open("w", encoding="utf-8") as f:
            f.write(badge)

        log.info(f"Reports generated in {report_dir}")

    def _generate_json_report(self) -> dict:
        """Generate JSON report with link health data."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        health_score = 0
        if self.links_checked > 0:
            health_score = (self.valid_links / self.links_checked) * 100

        return {
            "version": "1.0",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "duration_seconds": round(duration, 2),
            "summary": {
                "total_links": self.links_checked,
                "valid_links": self.valid_links,
                "broken_links": self.broken_links,
                "redirect_links": self.redirect_links,
                "health_score": round(health_score, 2),
                "internal_links": sum(
                    1 for link in self.link_results if link.get("is_internal")
                ),
                "external_links": sum(
                    1 for link in self.link_results if not link.get("is_internal")
                ),
            },
            "details": self.link_results,
        }

    def _generate_html_report(self) -> str:
        """Generate HTML report with link health data."""
        json_report = self._generate_json_report()
        summary = json_report["summary"]

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Link Health Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .status-valid {{ color: green; }}
                .status-broken {{ color: red; }}
                .status-redirect {{ color: orange; }}
                .status-error {{ color: darkred; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #f5f5f5; }}
                .health-score {{ font-size: 24px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>🔗 Link Health Report</h1>
            <div class="summary">
                <h2>Summary</h2>
                <p><strong>Generated:</strong> {json_report["generated_at"]}</p>
                <p><strong>Duration:</strong> {json_report["duration_seconds"]} seconds</p>
                <p><strong>Total Links:</strong> {summary["total_links"]}</p>
                <p><strong>Valid Links:</strong> <span class="status-valid">{summary["valid_links"]}</span></p>
                <p><strong>Broken Links:</strong> <span class="status-broken">{summary["broken_links"]}</span></p>
                <p><strong>Redirect Links:</strong> <span class="status-redirect">{summary["redirect_links"]}</span></p>
                <p><strong>Health Score:</strong> <span class="health-score">{summary["health_score"]}%</span></p>
            </div>

            <h2>Details</h2>
            <table>
                <thead>
                    <tr>
                        <th>Source File</th>
                        <th>Link URL</th>
                        <th>Link Text</th>
                        <th>Status</th>
                        <th>HTTP Code</th>
                    </tr>
                </thead>
                <tbody>
        """

        for link in self.link_results:
            status_class = f"status-{link['status']}"
            http_code = link["http_code"] if link["http_code"] else "N/A"

            html += f"""
                <tr>
                    <td>{link["source_file"]}</td>
                    <td><a href="{link["link_url"]}" target="_blank">{link["link_url"]}</a></td>
                    <td>{link["link_text"][:50]}...</td>
                    <td class="{status_class}">{link["status"]}</td>
                    <td>{http_code}</td>
                </tr>
            """

        html += """
            </tbody>
        </table>
        </body>
        </html>
        """

        return html

    def _generate_badge(self) -> str:
        """Generate SVG badge showing link health status."""
        health_score = (
            round((self.valid_links / self.links_checked) * 100)
            if self.links_checked > 0
            else 0
        )

        # Determine badge color based on health score
        if health_score >= 95:
            color = "#4c1"
            status = "passing"
        elif health_score >= 80:
            color = "#dbab09"
            status = "warning"
        else:
            color = "#e05d44"
            status = "failing"

        font_family = "Verdana, DejaVu Sans, sans-serif"
        return f"""
        <svg xmlns="http://www.w3.org/2000/svg" width="120" height="20">
            <linearGradient id="b" x2="0" y2="100%">
                <stop offset="0" stop-color="{color}" stop-opacity=".7"/>
                <stop offset="1" stop-color="{color}"/></linearGradient>
            <rect rx="3" width="120" height="20" fill="{color}"/>
            <rect rx="3" x="70" width="50" height="20" fill="url(#b)"/>
            <path d="M70 0h50v20H70z" fill="url(#b)"/>
            <text x="10" y="14" fill="#fff" font-size="11"
                font-family="{font_family}">Link Health</text>
            <text x="75" y="14" fill="#fff" font-size="11"
                font-family="{font_family}" text-anchor="middle">
                {health_score}%
            </text>
            <text x="110" y="14" fill="#fff" font-size="11"
                font-family="{font_family}" text-anchor="end">{status}</text>
        </svg>
        """

    def _log_summary(self):
        """Log summary of link checking results."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        health_score = 0
        if self.links_checked > 0:
            health_score = (self.valid_links / self.links_checked) * 100

        log.info("=" * 50)
        log.info("🔗 LINK HEALTH SUMMARY")
        log.info("=" * 50)
        log.info(f"📊 Total Links Checked: {self.links_checked}")
        log.info(f"✅ Valid Links: {self.valid_links}")
        log.info(f"❌ Broken Links: {self.broken_links}")
        log.info(f"🔄 Redirect Links: {self.redirect_links}")
        log.info(f"🏥 Health Score: {health_score:.1f}%")
        log.info(f"⏱️  Duration: {duration:.2f} seconds")
        log.info("=" * 50)

        if self.broken_links > 0:
            log.warning(f"⚠️  Found {self.broken_links} broken links")
        else:
            log.info("🎉 All links are valid!")


def on_config(config):
    """MkDocs config hook to ensure plugin is properly configured."""
    return config
