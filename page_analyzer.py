#!/usr/bin/env python3
"""
Page Analyzer - Analyzes cookbook images to find missing pages
Extracts page numbers from images and correlates gaps with unmatched recipes.
"""

import json
import os
import sys
import base64
import argparse
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List
import requests
from backend import config, llm, image as img_utils


def analyze_image_with_ollama(image_path: str, prompt: str, model: str = "llava") -> Optional[str]:
    """Send an image to Ollama vision model for analysis."""
    # Encode image
    try:
        image_base64 = img_utils.encode_image_to_base64(image_path)
    except Exception as e:
        print(f"Error encoding image {image_path}: {e}")
        return None
        
    return llm.query_ollama(prompt, model, images=[image_base64])


def extract_page_numbers(image_path: str, model: str, max_retries: int = 2) -> dict:
    """
    Extract page number information from a cookbook image.
    
    Uses multiple prompts and retry logic to improve detection reliability.
    
    Returns dict with:
    - pages: list of page numbers shown (e.g., [25, 26] for a two-page spread)
    - total_pages: total pages in book if visible
    - raw_text: the raw page number text found
    """
    
    # Different prompts to try - some models respond better to different phrasings
    prompts = [
        # Primary prompt - detailed
        """Look carefully at the BOTTOM RIGHT and BOTTOM LEFT corners of this image for page numbers.

Page numbers in ebooks/digital cookbooks often appear as:
- "162-164 / 254" (current pages / total)
- "25-26 / 100"
- "Page 42 of 200"
- Just "42" or "42-43"

Look specifically at:
1. Bottom right corner - most common location
2. Bottom left corner
3. Top corners
4. Any navigation bar or footer area

Respond in this exact JSON format:
{
    "pages": [list each page number as an integer],
    "total_pages": total pages in book if shown (integer) or null,
    "raw_text": "copy the exact page number text you see"
}

Example: For "162-164 / 254" respond: {"pages": [162, 163, 164], "total_pages": 254, "raw_text": "162-164 / 254"}

Respond with ONLY the JSON.""",

        # Fallback prompt - simpler, more direct
        """What page numbers are shown in this image? Look in ALL corners, especially bottom-right.

Common formats: "162-164 / 254" or "Page 25" or "25-26"

Reply with JSON only:
{"pages": [numbers], "total_pages": number or null, "raw_text": "what you see"}""",

        # Last resort - very simple
        """Find any numbers in the corners of this image that look like page numbers (e.g., "162-164 / 254").

JSON response: {"pages": [integers], "total_pages": integer or null, "raw_text": "text"}"""
    ]
    
    best_result = {"pages": [], "total_pages": None, "raw_text": "extraction failed"}
    
    for attempt, prompt in enumerate(prompts[:max_retries + 1]):
        response = analyze_image_with_ollama(image_path, prompt, model)
        
        if response:
            result = parse_page_response(response)
            
            # If we found pages, return immediately
            if result.get("pages"):
                result["attempt"] = attempt + 1
                return result
            
            # Keep track of best result (even if empty, might have useful raw_text)
            if result.get("raw_text") and result["raw_text"] != "extraction failed":
                best_result = result
                best_result["attempt"] = attempt + 1
    
    return best_result


def parse_page_response(response: str) -> dict:
    """Parse the model response for page numbers with multiple fallback strategies."""
    
    result = {"pages": [], "total_pages": None, "raw_text": ""}
    
    if not response:
        return result
    
    # Try JSON parsing first
    try:
        json_str = response.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]
        
        parsed = json.loads(json_str.strip())
        
        if "pages" in parsed:
            # Handle various formats the model might return
            pages = parsed["pages"]
            if isinstance(pages, list):
                result["pages"] = [int(p) for p in pages if str(p).replace('-', '').isdigit()]
            elif isinstance(pages, (int, str)):
                result["pages"] = [int(pages)]
        
        if "total_pages" in parsed and parsed["total_pages"]:
            try:
                result["total_pages"] = int(parsed["total_pages"])
            except (ValueError, TypeError):
                pass
        
        result["raw_text"] = parsed.get("raw_text", "")
        
        return result
        
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Fallback: regex extraction from raw response
    # Look for patterns like "162-164 / 254" or "162-164/254" or "pages 162-164"
    
    # Pattern for "X-Y / Z" or "X-Y/Z" (page range with total)
    range_total_pattern = r'(\d+)\s*[-–]\s*(\d+)\s*/\s*(\d+)'
    match = re.search(range_total_pattern, response)
    if match:
        start, end, total = int(match.group(1)), int(match.group(2)), int(match.group(3))
        result["pages"] = list(range(start, end + 1))
        result["total_pages"] = total
        result["raw_text"] = match.group(0)
        result["parse_note"] = "Extracted via regex (range/total pattern)"
        return result
    
    # Pattern for "X / Y" (single page with total)
    single_total_pattern = r'(\d+)\s*/\s*(\d+)'
    match = re.search(single_total_pattern, response)
    if match:
        page, total = int(match.group(1)), int(match.group(2))
        result["pages"] = [page]
        result["total_pages"] = total
        result["raw_text"] = match.group(0)
        result["parse_note"] = "Extracted via regex (single/total pattern)"
        return result
    
    # Pattern for "X-Y" (page range without total)
    range_pattern = r'(\d+)\s*[-–]\s*(\d+)'
    match = re.search(range_pattern, response)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        # Sanity check - page numbers shouldn't be too far apart
        if end - start <= 10:
            result["pages"] = list(range(start, end + 1))
            result["raw_text"] = match.group(0)
            result["parse_note"] = "Extracted via regex (range pattern)"
            return result
    
    # Last resort: find any numbers that could be page numbers
    numbers = re.findall(r'\b(\d{1,4})\b', response)
    if numbers:
        # Filter to reasonable page numbers (1-9999)
        page_nums = [int(n) for n in numbers if 1 <= int(n) <= 9999]
        if page_nums:
            result["pages"] = [page_nums[0]]
            if len(page_nums) > 1:
                result["total_pages"] = page_nums[-1]
            result["raw_text"] = response[:100]
            result["parse_note"] = "Extracted via regex (number fallback)"
            return result
    
    result["raw_text"] = response[:100] if response else "no response"
    return result


def analyze_folder(folder_path: str, model: str, max_retries: int = 2) -> dict:
    """
    Analyze all images in a folder and extract page numbers.
    
    Returns analysis with:
    - pages_found: mapping of page numbers to image files
    - missing_pages: list of page numbers not found
    - page_ranges: continuous ranges that were captured
    """
    folder = Path(folder_path)
    image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
    
    image_files = sorted([
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in image_extensions
    ])
    
    if not image_files:
        return {"error": "No images found"}
    
    print(f"Found {len(image_files)} images to analyze")
    print("=" * 50)
    
    analysis = {
        "metadata": {
            "source_folder": str(folder_path),
            "analyzed_date": datetime.now().isoformat(),
            "model_used": model,
            "total_images": len(image_files)
        },
        "pages_found": {},  # page_num -> {file, raw_text}
        "files_analyzed": [],
        "total_book_pages": None,
        "missing_pages": [],
        "coverage": {}
    }
    
    all_pages = set()
    total_pages = None
    
    for i, image_path in enumerate(image_files):
        print(f"[{i+1}/{len(image_files)}] {image_path.name}...", end=" ", flush=True)
        
        result = extract_page_numbers(str(image_path), model, max_retries)
        
        file_info = {
            "file": image_path.name,
            "pages": result.get("pages", []),
            "raw_text": result.get("raw_text", "")
        }
        analysis["files_analyzed"].append(file_info)
        
        pages = result.get("pages", [])
        if pages:
            print(f"pages {pages}")
            for page in pages:
                all_pages.add(page)
                analysis["pages_found"][page] = {
                    "file": image_path.name,
                    "raw_text": result.get("raw_text", "")
                }
        else:
            print("no page numbers found")
        
        # Track total pages
        if result.get("total_pages") and not total_pages:
            total_pages = result["total_pages"]
            analysis["total_book_pages"] = total_pages
    
    # Calculate missing pages
    if all_pages:
        min_page = min(all_pages)
        max_page = max(all_pages)
        
        # Use total_pages if we found it, otherwise use max found
        end_page = total_pages if total_pages else max_page
        
        expected_pages = set(range(min_page, end_page + 1))
        missing = sorted(expected_pages - all_pages)
        analysis["missing_pages"] = missing
        
        # Calculate coverage
        analysis["coverage"] = {
            "first_page_found": min_page,
            "last_page_found": max_page,
            "pages_captured": len(all_pages),
            "pages_missing": len(missing),
            "coverage_percent": round(len(all_pages) / len(expected_pages) * 100, 1) if expected_pages else 0
        }
        
        # Find continuous ranges
        analysis["page_ranges"] = find_ranges(sorted(all_pages))
        analysis["missing_ranges"] = find_ranges(missing)
    
    return analysis


def find_ranges(numbers: List[int]) -> List[str]:
    """Convert a list of numbers into ranges like ['1-5', '10-15', '20']."""
    if not numbers:
        return []
    
    ranges = []
    start = numbers[0]
    end = numbers[0]
    
    for num in numbers[1:]:
        if num == end + 1:
            end = num
        else:
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            start = num
            end = num
    
    # Don't forget the last range
    if start == end:
        ranges.append(str(start))
    else:
        ranges.append(f"{start}-{end}")
    
    return ranges


def correlate_with_catalog(analysis: dict, catalog_path: str) -> dict:
    """
    Correlate missing pages with unmatched recipes from a catalog.
    
    Tries to estimate which missing pages might contain which recipes
    based on chapter order and page positions.
    """
    if not os.path.isfile(catalog_path):
        return {"error": f"Catalog not found: {catalog_path}"}
    
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    correlation = {
        "unmatched_recipes": [],
        "estimated_locations": [],
        "suggestions": []
    }
    
    # Get unmatched recipes from catalog
    unmatched = catalog.get("index", {}).get("unmatched", [])
    if not unmatched:
        # Try older format
        chapters = catalog.get("chapters", [])
        recipes = catalog.get("recipes", [])
        extracted_names = {r.get("name", "").lower() for r in recipes}
        
        for chapter in chapters:
            for recipe_name in chapter.get("recipe_list", []):
                if recipe_name.lower() not in extracted_names:
                    unmatched.append({
                        "name": recipe_name,
                        "chapter": chapter.get("chapter_title")
                    })
    
    correlation["unmatched_recipes"] = unmatched
    correlation["unmatched_count"] = len(unmatched)
    correlation["missing_pages_count"] = len(analysis.get("missing_pages", []))
    
    # Estimate: typically 2 recipes per page spread (4 pages = ~2-4 recipes)
    missing_pages = analysis.get("missing_pages", [])
    if missing_pages and unmatched:
        # Group missing pages into potential spreads
        spreads = []
        current_spread = [missing_pages[0]]
        
        for page in missing_pages[1:]:
            if page <= current_spread[-1] + 2:  # Adjacent or near pages
                current_spread.append(page)
            else:
                spreads.append(current_spread)
                current_spread = [page]
        spreads.append(current_spread)
        
        correlation["missing_page_groups"] = [
            {"pages": spread, "range": f"{spread[0]}-{spread[-1]}" if len(spread) > 1 else str(spread[0])}
            for spread in spreads
        ]
        
        # Generate suggestions
        recipes_per_spread = max(1, len(unmatched) // max(1, len(spreads)))
        
        correlation["suggestions"].append(
            f"You have {len(unmatched)} unmatched recipes and {len(missing_pages)} missing pages."
        )
        correlation["suggestions"].append(
            f"Missing pages are grouped into {len(spreads)} section(s)."
        )
        
        if len(spreads) > 0:
            correlation["suggestions"].append(
                f"Estimate: ~{recipes_per_spread} recipe(s) per missing section."
            )
            correlation["suggestions"].append(
                "Screenshot the following page ranges to capture missing recipes:"
            )
            for group in correlation["missing_page_groups"]:
                correlation["suggestions"].append(f"  • Pages {group['range']}")
    
    return correlation


def check_ollama_available(model: str) -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        # Use simple status text check first to be safe
        response = requests.get(config.OLLAMA_API_URL.replace("/api/generate", "/api/tags"), timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        model_names = [m.get("name", "").split(":")[0] for m in models]
        
        if model.split(":")[0] not in model_names:
            print(f"Model '{model}' not found. Available: {model_names}")
            return False
        return True
    except requests.exceptions.ConnectionError:
        print("Ollama is not running. Start with: ollama serve")
        return False
    except Exception as e:
        print(f"Error checking Ollama: {e}")
        return False


def analyze_catalog_for_failures(catalog_path: str, source_folder: str = None) -> dict:
    """
    Analyze a recipe catalog JSON to find processing failures and missed recipes.
    
    Returns dict with:
    - failed_files: files that failed to process (type: other, errors, etc.)
    - partial_only: files that only produced partial recipes
    - low_confidence: files with low confidence classification
    - skipped: files that were skipped
    - unmatched_recipes: recipes listed in chapters but not extracted
    - summary: overall stats
    """
    
    with open(catalog_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    
    # Get source folder from catalog if not provided
    if not source_folder:
        source_folder = catalog.get("metadata", {}).get("source_folder", "")
    
    processing_log = catalog.get("processing_log", [])
    
    failed_files = []
    partial_only = []
    low_confidence = []
    skipped_files = []
    error_files = []
    
    for entry in processing_log:
        filename = entry.get("file", "")
        page_type = entry.get("page_type", "unknown")
        classification = entry.get("classification", {})
        confidence = classification.get("confidence", "unknown")
        recipes_extracted = entry.get("recipes_extracted", [])
        has_continuation = entry.get("has_continuation", False)
        status = entry.get("status", "")
        
        file_path = os.path.join(source_folder, filename) if source_folder else filename
        
        file_info = {
            "file": filename,
            "path": file_path,
            "page_type": page_type,
            "confidence": confidence,
            "recipes_extracted": recipes_extracted,
            "classification": classification
        }
        
        # Check for various failure modes
        if "error" in str(entry).lower() or page_type == "other":
            # Check if this was likely a recipe page that failed
            if classification.get("recipe_names_visible") or classification.get("has_recipe_start"):
                file_info["reason"] = "Classified as 'other' but had recipe indicators"
                file_info["priority"] = "high"
                failed_files.append(file_info)
            elif confidence == "low" and not classification.get("type"):
                # Low confidence AND no type means classification likely failed (API error)
                # We should retry these
                file_info["reason"] = "Classification failed (possible API error)"
                file_info["priority"] = "medium"
                failed_files.append(file_info)
            # Note: We no longer flag "low confidence other" as failed if it has a type
            # because "other" with low confidence could just be a legitimate non-recipe page
            # that the model wasn't sure about (intro, credits, etc.)
        
        elif page_type in ["recipe", "recipe_partial"]:
            # Recipe page but no recipes extracted
            if not recipes_extracted or recipes_extracted == ['none'] or len(recipes_extracted) == 0:
                if has_continuation:
                    file_info["reason"] = "Recipe page with only continuation, no complete recipes"
                    partial_only.append(file_info)
                else:
                    file_info["reason"] = "Recipe page but no recipes extracted"
                    failed_files.append(file_info)
            
            # Check if fewer recipes than expected
            expected = len(classification.get("recipe_names_visible", []))
            actual = len([r for r in recipes_extracted if r and r != 'none'])
            if expected > 0 and actual < expected:
                file_info["reason"] = f"Expected {expected} recipes, got {actual}"
                file_info["expected"] = expected
                file_info["actual"] = actual
                if file_info not in failed_files:
                    failed_files.append(file_info)
        
        elif "skipped" in status.lower():
            file_info["reason"] = status
            skipped_files.append(file_info)
        
        if confidence == "low" and file_info not in failed_files:
            file_info["reason"] = f"Low confidence {page_type} classification"
            low_confidence.append(file_info)
    
    # Find unmatched recipes (listed in chapters but not extracted)
    unmatched = catalog.get("index", {}).get("unmatched", [])
    
    # Summary
    total_processed = len(processing_log)
    total_recipes = len(catalog.get("recipes", []))
    
    return {
        "catalog_path": catalog_path,
        "source_folder": source_folder,
        "failed_files": failed_files,
        "partial_only": partial_only,
        "low_confidence": low_confidence,
        "skipped_files": skipped_files,
        "unmatched_recipes": unmatched,
        "summary": {
            "total_files_processed": total_processed,
            "total_recipes_extracted": total_recipes,
            "failed_count": len(failed_files),
            "partial_only_count": len(partial_only),
            "low_confidence_count": len(low_confidence),
            "skipped_count": len(skipped_files),
            "unmatched_recipe_count": len(unmatched)
        }
    }


def print_catalog_analysis(analysis: dict):
    """Print a formatted catalog analysis report."""
    print("\n" + "=" * 60)
    print("📊 CATALOG ANALYSIS REPORT")
    print("=" * 60)
    
    summary = analysis.get("summary", {})
    print(f"\nTotal files processed: {summary.get('total_files_processed', 0)}")
    print(f"Total recipes extracted: {summary.get('total_recipes_extracted', 0)}")
    
    # Failed files
    failed = analysis.get("failed_files", [])
    if failed:
        print(f"\n❌ Failed/Incomplete Extractions ({len(failed)}):")
        for f in failed:
            print(f"   • {f['file']}")
            print(f"     Reason: {f.get('reason', 'Unknown')}")
            if f.get('expected'):
                print(f"     Expected: {f['expected']} recipes, Got: {f['actual']}")
    
    # Partial only
    partial = analysis.get("partial_only", [])
    if partial:
        print(f"\n⚠️  Partial Recipes Only ({len(partial)}):")
        for f in partial:
            print(f"   • {f['file']} - {f.get('reason', '')}")
    
    # Low confidence
    low_conf = analysis.get("low_confidence", [])
    if low_conf:
        print(f"\n🔍 Low Confidence Classifications ({len(low_conf)}):")
        for f in low_conf[:5]:
            print(f"   • {f['file']} - {f.get('reason', '')}")
        if len(low_conf) > 5:
            print(f"   ... and {len(low_conf) - 5} more")
    
    # Unmatched recipes
    unmatched = analysis.get("unmatched_recipes", [])
    if unmatched:
        print(f"\n📋 Unmatched Recipes ({len(unmatched)}):")
        for r in unmatched[:10]:
            print(f"   • {r.get('name', 'Unknown')} ({r.get('chapter', 'Unknown chapter')})")
        if len(unmatched) > 10:
            print(f"   ... and {len(unmatched) - 10} more")
    
    # Files to reprocess
    reprocess = failed + partial
    if reprocess:
        print(f"\n🔄 Files recommended for reprocessing: {len(reprocess)}")
    else:
        print(f"\n✅ No files need reprocessing!")
    
    print("\n" + "=" * 60)


def reprocess_failed_files(analysis: dict, model: str, backup_model: str = None, 
                           dry_run: bool = True, catalog_path: str = None,
                           cataloger_script: str = "recipe_cataloger.py",
                           include_low_confidence: bool = False,
                           api_key: str = None) -> dict:
    """
    Reprocess files that failed during initial catalog creation.
    
    Args:
        analysis: Output from analyze_catalog_for_failures()
        model: Primary model to use
        backup_model: Fallback model for large files
        dry_run: If True, only print commands without executing
        catalog_path: Path to catalog JSON for --append-to
        cataloger_script: Path to recipe_cataloger.py script
        include_low_confidence: Also reprocess low confidence pages (may include non-recipe pages)
        api_key: Anthropic API key for Claude models
    
    Returns:
        Dict with results of reprocessing
    """
    import subprocess
    import shlex
    
    # Combine failed and partial-only files
    files_to_reprocess = analysis.get("failed_files", []) + analysis.get("partial_only", [])
    
    # Optionally include low confidence pages
    if include_low_confidence:
        low_conf = analysis.get("low_confidence", [])
        # Avoid duplicates
        existing_files = {f.get("file") for f in files_to_reprocess}
        for f in low_conf:
            if f.get("file") not in existing_files:
                f["reason"] = f.get("reason", "Low confidence classification")
                files_to_reprocess.append(f)
        if low_conf:
            print(f"ℹ️  Including {len(low_conf)} low-confidence pages (--include-low-confidence)")
    
    if not files_to_reprocess:
        print("✅ No files need reprocessing!")
        return {"reprocessed": 0, "success": 0, "failed": 0}
    
    # Use catalog path from analysis if not provided
    if not catalog_path:
        catalog_path = analysis.get("catalog_path")
    
    source_folder = analysis.get("source_folder", "")
    
    print(f"\n{'🔍 DRY RUN - ' if dry_run else ''}Reprocessing {len(files_to_reprocess)} files...")
    print("=" * 60)
    
    results = {
        "reprocessed": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "commands": [],
        "errors": []
    }
    
    for file_info in files_to_reprocess:
        filename = file_info.get("file", "")
        file_path = file_info.get("path", "")
        
        # If path doesn't exist, try to construct it
        if not os.path.isfile(file_path):
            if source_folder and os.path.isfile(os.path.join(source_folder, filename)):
                file_path = os.path.join(source_folder, filename)
            else:
                print(f"⚠️  Skipping {filename} - file not found")
                results["skipped"] += 1
                continue
        
        # Build command
        cmd_parts = [
            "python", cataloger_script,
            "-f", file_path,
            "-m", model
        ]
        
        if backup_model:
            cmd_parts.extend(["--backup-model", backup_model])
        
        if api_key:
            cmd_parts.extend(["--api-key", api_key])
        
        if catalog_path:
            cmd_parts.extend(["--append-to", catalog_path])
        
        cmd_str = " ".join(shlex.quote(p) for p in cmd_parts)
        results["commands"].append(cmd_str)
        
        print(f"\n📄 {filename}")
        print(f"   Reason: {file_info.get('reason', 'Unknown')}")
        
        if dry_run:
            print(f"   Command: {cmd_str}")
        else:
            print(f"   Running: {cmd_str}")
            try:
                result = subprocess.run(
                    cmd_parts,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per file
                )
                
                results["reprocessed"] += 1
                
                if result.returncode == 0:
                    # Parse output to find what was extracted
                    stdout = result.stdout
                    
                    # Look for recipe extraction info
                    extracted_match = re.search(r'Extracted (\d+) recipe\(s\): (.+?)(?:\n|$)', stdout)
                    added_match = re.search(r'Added: (\d+) recipe\(s\)', stdout)
                    updated_match = re.search(r'Updated: (\d+) recipe\(s\)', stdout)
                    type_match = re.search(r'Type: (\w+)', stdout)
                    backup_used = "using backup model" in stdout
                    
                    page_type = type_match.group(1) if type_match else "unknown"
                    
                    if extracted_match:
                        count = extracted_match.group(1)
                        names = extracted_match.group(2).strip()
                        results["success"] += 1
                        backup_note = " (via backup model)" if backup_used else ""
                        print(f"   ✅ Extracted {count}: {names}{backup_note}")
                    elif added_match or updated_match:
                        added = added_match.group(1) if added_match else "0"
                        updated = updated_match.group(1) if updated_match else "0"
                        results["success"] += 1
                        print(f"   ✅ Added: {added}, Updated: {updated}")
                    elif page_type in ["article", "photo", "chapter"]:
                        results["success"] += 1
                        print(f"   ℹ️  Page type: {page_type} (no recipe content)")
                    elif "0 recipe(s)" in stdout or "Extracted 0" in stdout:
                        results["success"] += 1  # Completed but no recipes
                        print(f"   ⚠️  No recipes extracted (page type: {page_type})")
                    else:
                        results["success"] += 1
                        print(f"   ⚠️  Completed (type: {page_type}) - check results")
                else:
                    results["failed"] += 1
                    error_msg = result.stderr[:200] if result.stderr else result.stdout[:200] if result.stdout else "Unknown error"
                    results["errors"].append({
                        "file": filename,
                        "error": error_msg
                    })
                    print(f"   ❌ Failed: {error_msg[:100]}")
                    
            except subprocess.TimeoutExpired:
                results["failed"] += 1
                results["errors"].append({"file": filename, "error": "Timeout"})
                print(f"   ❌ Timeout")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({"file": filename, "error": str(e)})
                print(f"   ❌ Error: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    if dry_run:
        print(f"🔍 DRY RUN COMPLETE")
        print(f"   Would reprocess: {len(files_to_reprocess)} files")
        print(f"   Skipped (not found): {results['skipped']}")
        print(f"\nTo actually reprocess, run without --dry-run")
    else:
        print(f"✅ REPROCESSING COMPLETE")
        print(f"   Processed: {results['reprocessed']}")
        print(f"   Success: {results['success']}")
        print(f"   Failed: {results['failed']}")
        print(f"   Skipped: {results['skipped']}")
    
    print("=" * 60)
    
    return results


def print_analysis_report(analysis: dict, correlation: dict = None):
    """Print a formatted analysis report."""
    print("\n" + "=" * 60)
    print("📖 PAGE ANALYSIS REPORT")
    print("=" * 60)
    
    coverage = analysis.get("coverage", {})
    print(f"\nImages analyzed: {analysis['metadata']['total_images']}")
    print(f"Total book pages: {analysis.get('total_book_pages', 'Unknown')}")
    print(f"Pages captured: {coverage.get('pages_captured', 0)}")
    print(f"Pages missing: {coverage.get('pages_missing', 0)}")
    print(f"Coverage: {coverage.get('coverage_percent', 0)}%")
    
    # Page ranges captured
    ranges = analysis.get("page_ranges", [])
    if ranges:
        print(f"\nPages captured: {', '.join(ranges)}")
    
    # Missing pages
    missing_ranges = analysis.get("missing_ranges", [])
    if missing_ranges:
        print(f"\n⚠️  Missing pages: {', '.join(missing_ranges)}")
    else:
        print("\n✅ No missing pages detected!")
    
    # Correlation with recipes
    if correlation and "error" not in correlation:
        print("\n" + "-" * 60)
        print("📋 RECIPE CORRELATION")
        print("-" * 60)
        
        print(f"Unmatched recipes: {correlation.get('unmatched_count', 0)}")
        
        unmatched = correlation.get("unmatched_recipes", [])
        if unmatched:
            print("\nRecipes not yet captured:")
            for recipe in unmatched[:10]:
                print(f"  • {recipe.get('name')} ({recipe.get('chapter', 'Unknown chapter')})")
            if len(unmatched) > 10:
                print(f"  ... and {len(unmatched) - 10} more")
        
        suggestions = correlation.get("suggestions", [])
        if suggestions:
            print("\n💡 Suggestions:")
            for suggestion in suggestions:
                print(f"  {suggestion}")
    
    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze cookbook images to find missing pages and correlate with unmatched recipes"
    )
    parser.add_argument(
        "folder",
        nargs="?",
        help="Path to folder containing cookbook images"
    )
    parser.add_argument(
        "-f", "--file",
        help="Test a single image file"
    )
    parser.add_argument(
        "-m", "--model",
        default="llava",
        help="Ollama vision model to use (default: llava)"
    )
    parser.add_argument(
        "-c", "--catalog",
        help="Path to recipe catalog JSON to correlate missing pages with unmatched recipes"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path (default: page_analysis.json in input folder)"
    )
    parser.add_argument(
        "-r", "--retries",
        type=int,
        default=2,
        help="Max retry attempts per image if page numbers not found (default: 2)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if Ollama and model are available"
    )
    
    # New catalog analysis arguments
    parser.add_argument(
        "--analyze-catalog",
        metavar="CATALOG_PATH",
        help="Analyze a recipe catalog JSON to find failed/missed extractions"
    )
    parser.add_argument(
        "--reprocess",
        action="store_true",
        help="Reprocess failed files (use with --analyze-catalog)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be reprocessed without actually doing it"
    )
    parser.add_argument(
        "--backup-model",
        help="Backup model for large files when reprocessing (e.g., qwen2-vl:8b)"
    )
    parser.add_argument(
        "--cataloger-script",
        default="recipe_cataloger.py",
        help="Path to recipe_cataloger.py script (default: recipe_cataloger.py)"
    )
    parser.add_argument(
        "--source-folder",
        help="Override source folder for finding image files during reprocessing"
    )
    parser.add_argument(
        "--include-low-confidence",
        action="store_true",
        help="Also reprocess pages with low confidence classifications (may include non-recipe pages)"
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key for Claude models (passed to recipe_cataloger for reprocessing)"
    )
    
    args = parser.parse_args()
    
    # Catalog analysis mode
    if args.analyze_catalog:
        if not os.path.isfile(args.analyze_catalog):
            print(f"Error: Catalog file not found: {args.analyze_catalog}")
            sys.exit(1)
        
        print(f"Analyzing catalog: {args.analyze_catalog}")
        
        # Analyze the catalog
        analysis = analyze_catalog_for_failures(args.analyze_catalog, args.source_folder)
        print_catalog_analysis(analysis)
        
        # Reprocess if requested
        if args.reprocess or args.dry_run:
            if not args.model:
                print("Error: --model is required for reprocessing")
                sys.exit(1)
            
            reprocess_failed_files(
                analysis=analysis,
                model=args.model,
                backup_model=args.backup_model,
                dry_run=args.dry_run or not args.reprocess,
                catalog_path=args.analyze_catalog,
                cataloger_script=args.cataloger_script,
                include_low_confidence=args.include_low_confidence,
                api_key=args.api_key or os.environ.get("ANTHROPIC_API_KEY")
            )
        
        sys.exit(0)
    
    # Check Ollama for page analysis modes
    if not args.analyze_catalog:
        if not check_ollama_available(args.model):
            sys.exit(1)
    
    if args.check_only:
        print(f"Ollama is running and model '{args.model}' is available!")
        sys.exit(0)
    
    # Single file test mode
    if args.file:
        if not os.path.isfile(args.file):
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        
        print(f"Testing single file: {args.file}")
        print(f"Model: {args.model}")
        print(f"Max retries: {args.retries}")
        print("=" * 50)
        
        result = extract_page_numbers(args.file, args.model, args.retries)
        
        print(f"\nResults:")
        print(f"  Pages found: {result.get('pages', [])}")
        print(f"  Total pages: {result.get('total_pages', 'N/A')}")
        print(f"  Raw text: {result.get('raw_text', 'N/A')}")
        if result.get('attempt'):
            print(f"  Found on attempt: {result['attempt']}")
        if result.get('parse_note'):
            print(f"  Parse method: {result['parse_note']}")
        
        print("=" * 50)
        sys.exit(0)
    
    # Folder mode - verify folder exists
    if not args.folder:
        parser.print_help()
        print("\nError: Please provide a folder path or use -f/--file to test a single image")
        print("       Or use --analyze-catalog to analyze a recipe catalog for failures")
        sys.exit(1)
    
    # Verify folder
    if not os.path.isdir(args.folder):
        print(f"Error: Folder not found: {args.folder}")
        sys.exit(1)
    
    # Analyze pages
    analysis = analyze_folder(args.folder, args.model, args.retries)
    
    if "error" in analysis:
        print(f"Error: {analysis['error']}")
        sys.exit(1)
    
    # Correlate with catalog if provided
    correlation = None
    if args.catalog:
        correlation = correlate_with_catalog(analysis, args.catalog)
        analysis["correlation"] = correlation
    
    # Print report
    print_analysis_report(analysis, correlation)
    
    # Save results
    output_path = args.output or os.path.join(args.folder, "page_analysis.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    print(f"\nAnalysis saved to: {output_path}")


if __name__ == "__main__":
    main()
