#!/usr/bin/env python3
import os
import json
import time
import requests
import pyfiglet
import platform
import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich import print
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax

# Initialize console
console = Console()

@dataclass
class KnowledgePanelData:
    """Data structure for Knowledge Panel information"""
    title: str
    description: str
    attributes: Dict[str, str]
    related_topics: List[str]
    source_urls: List[str]
    timestamp: str

class BannerManager:
    @staticmethod
    def display_banner(username: str, current_time: str) -> None:
        """Display application banner with user information"""
        # Create banner using pyfiglet
        banner_text = pyfiglet.figlet_format("Knowledge Panel Extractor", font="slant")
        console.print(Panel(f"[bold cyan]{banner_text}[/bold cyan]"))
        
        # Create info table
        info_table = Table.grid(padding=1)
        info_table.add_row("[bold green]User:[/bold green]", username)
        info_table.add_row("[bold blue]Time:[/bold blue]", current_time)
        info_table.add_row("[bold yellow]System:[/bold yellow]", f"{platform.system()} {platform.release()}")
        
        console.print(Panel(info_table))
        
        # Tool information
        console.print(Panel(
            "[bold magenta]Knowledge Panel Data Extractor[/bold magenta]\n"
            "• Automated Data Extraction\n"
            "• Structured Output Formats\n"
            "• Smart Caching System\n"
            "• Advanced Error Handling",
            title="Tool Information",
            border_style="blue"
        ))

class KnowledgePanelExtractor:
    def __init__(self):
        self.config_dir = Path.home() / '.knowledge_extractor'
        self.cache_dir = self.config_dir / 'cache'
        self.output_dir = self.config_dir / 'output'
        self.initialize_directories()
        self.setup_webdriver()

    def initialize_directories(self) -> None:
        """Initialize necessary directories"""
        try:
            for directory in [self.config_dir, self.cache_dir, self.output_dir]:
                directory.mkdir(parents=True, exist_ok=True)
                directory.chmod(0o700)  # Secure permissions
            
            console.print("[bold green]✓ Directories initialized successfully[/bold green]")
        except Exception as e:
            console.print(f"[bold red]Directory initialization error: {str(e)}[/bold red]")
            raise

    def setup_webdriver(self) -> None:
        """Setup Chrome webdriver with optimal configurations"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920x1080')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            console.print("[bold green]✓ WebDriver initialized successfully[/bold green]")
        except Exception as e:
            console.print(f"[bold red]WebDriver initialization error: {str(e)}[/bold red]")
            raise

    def extract_knowledge_panel(self, query: str) -> Optional[KnowledgePanelData]:
        """Extract data from Google Knowledge Panel"""
        try:
            # Check cache first
            cached_data = self._check_cache(query)
            if cached_data:
                console.print("[yellow]Retrieved from cache[/yellow]")
                return cached_data

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%")
            ) as progress:
                # Search setup
                task = progress.add_task("[cyan]Extracting knowledge panel...", total=100)
                progress.update(task, advance=10)
                
                # Perform search
                self._perform_search(query)
                progress.update(task, advance=20)
                
                # Wait for knowledge panel
                panel_data = self._extract_panel_data()
                progress.update(task, advance=40)
                
                if panel_data:
                    # Process and structure data
                    structured_data = self._structure_data(panel_data)
                    progress.update(task, advance=20)
                    
                    # Cache the results
                    self._cache_results(query, structured_data)
                    progress.update(task, advance=10)
                    
                    return structured_data
                
                return None

        except Exception as e:
            console.print(f"[bold red]Extraction error: {str(e)}[/bold red]")
            return None

    def _check_cache(self, query: str) -> Optional[KnowledgePanelData]:
        """Check if data exists in cache"""
        cache_file = self.cache_dir / f"{hash(query)}.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    # Check if cache is less than 24 hours old
                    cache_time = datetime.datetime.fromisoformat(data['timestamp'])
                    if (datetime.datetime.utcnow() - cache_time).total_seconds() < 86400:
                        return KnowledgePanelData(**data)
            except Exception:
                pass
        return None

    def _perform_search(self, query: str) -> None:
        """Perform Google search and wait for results"""
        search_url = f"https://www.google.com/search?q={query}"
        self.driver.get(search_url)
        time.sleep(2)  # Allow page to load

    def _extract_panel_data(self) -> Optional[Dict[str, Any]]:
        """Extract data from knowledge panel"""
        try:
            # Wait for knowledge panel
            panel = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "knowledge-panel"))
            )
            
            # Extract basic information
            data = {
                'title': self._safe_extract(panel, './/h2'),
                'description': self._safe_extract(panel, './/div[@class="kno-rdesc"]'),
                'attributes': self._extract_attributes(panel),
                'related_topics': self._extract_related_topics(panel),
                'source_urls': self._extract_sources(panel),
                'timestamp': datetime.datetime.utcnow().isoformat()
            }
            
            return data
            
        except Exception as e:
            console.print(f"[yellow]No knowledge panel found: {str(e)}[/yellow]")
            return None

    def _safe_extract(self, element, xpath: str) -> str:
        """Safely extract text from element"""
        try:
            result = element.find_element(By.XPATH, xpath)
            return result.text.strip()
        except Exception:
            return ""

    def _extract_attributes(self, panel) -> Dict[str, str]:
        """Extract attributes from knowledge panel"""
        attributes = {}
        try:
            attribute_rows = panel.find_elements(By.CLASS_NAME, "kno-fv")
            for row in attribute_rows:
                key = self._safe_extract(row, './/span[@class="w8qArf"]')
                value = self._safe_extract(row, './/span[@class="LrzXr kno-fv"]')
                if key and value:
                    attributes[key] = value
        except Exception:
            pass
        return attributes

    def _extract_related_topics(self, panel) -> List[str]:
        """Extract related topics"""
        topics = []
        try:
            topic_elements = panel.find_elements(By.CLASS_NAME, "kno-fb-ctx")
            topics = [elem.text.strip() for elem in topic_elements if elem.text.strip()]
        except Exception:
            pass
        return topics

    def _extract_sources(self, panel) -> List[str]:
        """Extract source URLs"""
        sources = []
        try:
            source_elements = panel.find_elements(By.XPATH, './/a[@class="ruhjFe NJLBac fl"]')
            sources = [elem.get_attribute('href') for elem in source_elements if elem.get_attribute('href')]
        except Exception:
            pass
        return sources

    def _structure_data(self, data: Dict[str, Any]) -> KnowledgePanelData:
        """Structure extracted data"""
        return KnowledgePanelData(**data)

    def _cache_results(self, query: str, data: KnowledgePanelData) -> None:
        """Cache extracted data"""
        try:
            cache_file = self.cache_dir / f"{hash(query)}.json"
            with open(cache_file, 'w') as f:
                json.dump(vars(data), f, indent=2)
        except Exception as e:
            console.print(f"[yellow]Caching error: {str(e)}[/yellow]")

    def save_results(self, data: KnowledgePanelData, format: str = 'json') -> str:
        """Save results in specified format"""
        timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output_file = self.output_dir / f"knowledge_panel_{timestamp}.{format}"
        
        try:
            if format == 'json':
                with open(output_file, 'w') as f:
                    json.dump(vars(data), f, indent=2)
            elif format == 'txt':
                with open(output_file, 'w') as f:
                    f.write(f"Title: {data.title}\n")
                    f.write(f"Description: {data.description}\n\n")
                    f.write("Attributes:\n")
                    for key, value in data.attributes.items():
                        f.write(f"  {key}: {value}\n")
                    f.write("\nRelated Topics:\n")
                    for topic in data.related_topics:
                        f.write(f"  • {topic}\n")
                    f.write("\nSources:\n")
                    for url in data.source_urls:
                        f.write(f"  • {url}\n")
            
            return str(output_file)
            
        except Exception as e:
            console.print(f"[bold red]Error saving results: {str(e)}[/bold red]")
            return ""

    def display_results(self, data: KnowledgePanelData) -> None:
        """Display extracted data in a formatted table"""
        # Create main table
        table = Table(title="Knowledge Panel Data", show_header=True, header_style="bold magenta")
        table.add_column("Field")
        table.add_column("Content")
        
        # Add basic information
        table.add_row("Title", data.title)
        table.add_row("Description", data.description)
        
        # Add attributes
        attributes_text = "\n".join([f"{k}: {v}" for k, v in data.attributes.items()])
        table.add_row("Attributes", attributes_text)
        
        # Add related topics
        topics_text = "\n".join([f"• {topic}" for topic in data.related_topics])
        table.add_row("Related Topics", topics_text)
        
        # Add sources
        sources_text = "\n".join([f"• {url}" for url in data.source_urls])
        table.add_row("Sources", sources_text)
        
        console.print(table)

    def cleanup(self) -> None:
        """Clean up resources"""
        try:
            self.driver.quit()
        except Exception:
            pass

def main():
    try:
        # Display banner
        BannerManager.display_banner(
            username="gaytri1111",
            current_time=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # Initialize extractor
        extractor = KnowledgePanelExtractor()
        
        while True:
            # Get search query
            query = Prompt.ask("\n[bold cyan]Enter search query for knowledge panel extraction")
            
            if query.lower() in ['exit', 'quit']:
                break
            
            # Extract data
            data = extractor.extract_knowledge_panel(query)
            
            if data:
                # Display results
                extractor.display_results(data)
                
                # Save results
                if Confirm.ask("\nSave results?"):
                    format_choice = Prompt.ask(
                        "Choose format",
                        choices=["json", "txt"],
                        default="json"
                    )
                    output_file = extractor.save_results(data, format_choice)
                    if output_file:
                        console.print(f"[green]Results saved to: {output_file}[/green]")
            else:
                console.print("[yellow]No knowledge panel found for this query[/yellow]")
            
            # Continue?
            if not Confirm.ask("\nExtract another knowledge panel?"):
                break
        
        # Cleanup
        extractor.cleanup()
        console.print("\n[bold green]Thank you for using Knowledge Panel Extractor![/bold green]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {str(e)}[/bold red]")
        raise

if __name__ == "__main__":
    main()
