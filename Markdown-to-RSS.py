# Markdown-to-RSS.py
# Usage: python script_name.py input.md output.rss --title "My Blog Feed" --description "A feed of my latest blog posts" --link "https://example.com/feed" --date-format "%Y-%m-%d" --log-level INFO

import markdown
import xml.etree.ElementTree as ET
from datetime import datetime
import re
import logging
from typing import List, Optional, NamedTuple
from html import escape
import bleach
import os
import argparse

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Article(NamedTuple):
    title: str
    content: str
    date: Optional[datetime]
    categories: List[str]
    author: Optional[str]

class MarkdownParsingError(Exception):
    pass

def sanitize_html(html_content: str) -> str:
    allowed_tags = [
        'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol', 'strong', 'ul',
        'p', 'br', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre'
    ]
    allowed_attributes = {
        'a': ['href', 'title'],
        'abbr': ['title'],
        'acronym': ['title'],
    }
    return bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attributes)

def parse_markdown(markdown_content: str, date_format: str = "%Y-%m-%d") -> List[Article]:
    try:
        # Convert Markdown to HTML
        html_content = markdown.markdown(markdown_content)
        
        # Parse the HTML content to extract items
        items = re.findall(r'<h1>(.*?)</h1>(.*?)(?=<h1>|$)', html_content, re.DOTALL)
        
        if not items:
            raise MarkdownParsingError("No articles found in the Markdown content.")
        
        parsed_items = []
        for item_title, item_content in items:
            # Extract date
            date_pattern = r'\s*(\d{4}[-/]\d{2}[-/]\d{2})'
            date_match = re.search(date_pattern, item_content)
            if date_match:
                try:
                    date = datetime.strptime(date_match.group(1), date_format)
                    item_content = item_content[:date_match.start()] + item_content[date_match.end():]
                except ValueError:
                    logging.warning(f"Invalid date format for article '{item_title}'. Expected format: {date_format}")
                    date = None
            else:
                date = None
                logging.warning(f"No date found for article '{item_title}'.")
            
            # Extract categories
            categories = []
            category_pattern = r'Categories:\s*(.*?)(?:\n|$)'
            category_match = re.search(category_pattern, item_content)
            if category_match:
                categories = [cat.strip() for cat in category_match.group(1).split(',')]
                item_content = item_content[:category_match.start()] + item_content[category_match.end():]
            
            # Extract author
            author_pattern = r'Author:\s*(.*?)(?:\n|$)'
            author_match = re.search(author_pattern, item_content)
            if author_match:
                author = author_match.group(1).strip()
                item_content = item_content[:author_match.start()] + item_content[author_match.end():]
            else:
                author = None
            
            # Sanitize the HTML content
            item_content = sanitize_html(item_content)
            
            parsed_items.append(Article(escape(item_title.strip()), item_content.strip(), date, categories, author))
        
        return parsed_items
    except Exception as e:
        raise MarkdownParsingError(f"Error parsing Markdown content: {str(e)}")

def markdown_to_rss(markdown_content: str, feed_title: str, feed_description: str, feed_link: str, date_format: str = "%Y-%m-%d") -> str:
    try:
        # Create the RSS feed structure
        rss = ET.Element("rss", version="2.0")
        channel = ET.SubElement(rss, "channel")

        # Add feed information
        ET.SubElement(channel, "title").text = escape(feed_title)
        ET.SubElement(channel, "description").text = escape(feed_description)
        ET.SubElement(channel, "link").text = escape(feed_link)

        # Parse markdown content
        articles = parse_markdown(markdown_content, date_format)

        # Add items to the feed
        for article in articles:
            item = ET.SubElement(channel, "item")
            ET.SubElement(item, "title").text = article.title
            ET.SubElement(item, "description").text = article.content
            
            if article.date:
                pub_date = article.date.strftime("%a, %d %b %Y %H:%M:%S +0000")
            else:
                logging.warning(f"Using current date for article '{article.title}'.")
                pub_date = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            
            ET.SubElement(item, "pubDate").text = pub_date
            
            for category in article.categories:
                ET.SubElement(item, "category").text = escape(category)
            
            if article.author:
                ET.SubElement(item, "author").text = escape(article.author)

        # Convert the XML tree to a string
        return ET.tostring(rss, encoding="unicode", xml_declaration=True)
    except Exception as e:
        logging.error(f"Error generating RSS feed: {str(e)}")
        raise

def read_markdown_file(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except IOError as e:
        logging.error(f"Error reading file {file_path}: {str(e)}")
        raise

def write_rss_file(rss_content: str, file_path: str) -> None:
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(rss_content)
        logging.info(f"RSS feed successfully written to {file_path}")
    except IOError as e:
        logging.error(f"Error writing to file {file_path}: {str(e)}")
        raise

def process_markdown_file(input_file: str, output_file: str, feed_title: str, feed_description: str, feed_link: str, date_format: str = "%Y-%m-%d") -> None:
    try:
        markdown_content = read_markdown_file(input_file)
        rss_feed = markdown_to_rss(markdown_content, feed_title, feed_description, feed_link, date_format)
        write_rss_file(rss_feed, output_file)
        logging.info(f"Successfully processed {input_file} and generated {output_file}")
    except Exception as e:
        logging.error(f"Error processing file {input_file}: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Convert Markdown files to RSS feeds.")
    parser.add_argument("input_file", help="Path to the input Markdown file")
    parser.add_argument("output_file", help="Path to the output RSS file")
    parser.add_argument("--title", required=True, help="Title of the RSS feed")
    parser.add_argument("--description", required=True, help="Description of the RSS feed")
    parser.add_argument("--link", required=True, help="Link to the RSS feed")
    parser.add_argument("--date-format", default="%Y-%m-%d", help="Date format used in the Markdown file (default: %%Y-%%m-%%d)")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help="Set the logging level")

    args = parser.parse_args()

    # Set the logging level based on the user's choice
    logging.getLogger().setLevel(args.log_level)

    try:
        process_markdown_file(
            args.input_file,
            args.output_file,
            args.title,
            args.description,
            args.link,
            args.date_format
        )
        print(f"RSS feed generated successfully. Check {args.output_file}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()