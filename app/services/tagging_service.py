"""Service for auto-extracting tags from reference content."""

import re
from typing import Dict, Optional


class TaggingService:
    """Service for extracting metadata tags from reference content."""

    @staticmethod
    def extract_tags_from_filename(filename: str) -> Dict[str, Optional[str]]:
        """
        Extract tags from filename patterns.

        Args:
            filename: Filename to parse (e.g., "Lecture_5_Slide_12.pdf", "pre_midterm_notes.pdf")

        Returns:
            Dictionary with extracted tags:
            - slideset: Optional[str] - Slideset name (e.g., "Lecture_5")
            - slide_number: Optional[int] - Slide number
            - exam_region: Optional[str] - "pre" or "post" if detected
            - topic: Optional[str] - Topic name if detected
        """
        tags = {
            "slideset": None,
            "slide_number": None,
            "exam_region": None,
            "topic": None,
        }

        if not filename:
            return tags

        filename_lower = filename.lower()

        # Extract exam region from filename
        if "pre" in filename_lower and "midterm" in filename_lower:
            tags["exam_region"] = "pre"
        elif "post" in filename_lower and "midterm" in filename_lower:
            tags["exam_region"] = "post"
        elif "pre" in filename_lower and ("midterm" not in filename_lower):
            # Could be pre-midterm, but less certain
            tags["exam_region"] = "pre"
        elif "post" in filename_lower and ("midterm" not in filename_lower):
            tags["exam_region"] = "post"

        # Extract slideset pattern: Lecture_X, LectureX, Lecture_X_Y, etc.
        slideset_patterns = [
            r"lecture[_\s]*(\d+)",  # Lecture_5, Lecture 5, Lecture5
            r"lec[_\s]*(\d+)",  # Lec_5, Lec 5
            r"slideset[_\s]*(\d+)",  # Slideset_5
            r"week[_\s]*(\d+)",  # Week_5
        ]

        for pattern in slideset_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                slideset_num = match.group(1)
                # Try to find the full slideset name
                full_match = re.search(
                    rf"({'|'.join([p.replace(r'(\d+)', '') for p in slideset_patterns])})[_\s]*{slideset_num}",
                    filename,
                    re.IGNORECASE,
                )
                if full_match:
                    slideset_name = full_match.group(0).replace("_", "_").strip()
                    tags["slideset"] = slideset_name
                else:
                    tags["slideset"] = f"Lecture_{slideset_num}"
                break

        # Extract slide number pattern: Slide_X, SlideX, Slide_X_Y, etc.
        slide_patterns = [
            r"slide[_\s]*(\d+)",  # Slide_12, Slide 12, Slide12
            r"page[_\s]*(\d+)",  # Page_12 (sometimes used for slides)
        ]

        for pattern in slide_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                try:
                    tags["slide_number"] = int(match.group(1))
                    break
                except ValueError:
                    continue

        # Extract topic from filename (common patterns)
        # Look for topic-like words after common separators
        topic_patterns = [
            r"[-_]([a-z]+(?:_[a-z]+)*)[-_]?slide",  # topic-slide, topic_slide
            r"[-_]([a-z]+(?:_[a-z]+)*)\.pdf$",  # topic.pdf
            r"[-_]([a-z]+(?:_[a-z]+)*)[-_]?\d",  # topic-5, topic_5
        ]

        for pattern in topic_patterns:
            match = re.search(pattern, filename_lower)
            if match:
                topic = match.group(1).replace("_", " ").title()
                # Filter out common non-topic words
                if topic.lower() not in [
                    "lecture",
                    "slide",
                    "page",
                    "week",
                    "pre",
                    "post",
                    "midterm",
                    "final",
                ]:
                    tags["topic"] = topic
                    break

        return tags

    @staticmethod
    def extract_tags_from_metadata(metadata: Dict) -> Dict[str, Optional[str]]:
        """
        Extract tags from existing metadata.

        Args:
            metadata: Existing metadata dictionary

        Returns:
            Dictionary with extracted tags
        """
        tags = {
            "slideset": None,
            "slide_number": None,
            "exam_region": None,
            "topic": None,
        }

        # Check for existing tags in metadata
        if "slideset" in metadata:
            tags["slideset"] = metadata["slideset"]
        if "slide_number" in metadata:
            try:
                tags["slide_number"] = int(metadata["slide_number"])
            except (ValueError, TypeError):
                pass
        if "exam_region" in metadata:
            region = metadata["exam_region"]
            if region in ["pre", "post"]:
                tags["exam_region"] = region
        if "topic" in metadata:
            tags["topic"] = metadata["topic"]

        # Try to extract from source_file or source if present
        source_file = metadata.get("source_file") or metadata.get("source")
        if source_file:
            filename_tags = TaggingService.extract_tags_from_filename(str(source_file))
            # Merge filename tags (only if not already set)
            for key, value in filename_tags.items():
                if tags[key] is None and value is not None:
                    tags[key] = value

        return tags

    @staticmethod
    def merge_metadata(
        auto_tags: Dict, user_overrides: Optional[Dict] = None
    ) -> Dict:
        """
        Merge auto_tags and user_overrides, with user_overrides taking precedence.

        Args:
            auto_tags: Auto-extracted tags
            user_overrides: User manual overrides (optional)

        Returns:
            Merged metadata dictionary
        """
        merged = auto_tags.copy()

        if user_overrides:
            # User overrides take precedence
            for key, value in user_overrides.items():
                if value is not None:  # Only override if value is not None
                    merged[key] = value

        return merged

    @staticmethod
    def determine_exam_region_from_slide_number(
        slide_number: Optional[int], midterm_slide: Optional[int] = None
    ) -> Optional[str]:
        """
        Determine exam region based on slide number if midterm slide is known.

        Args:
            slide_number: Slide number
            midterm_slide: Slide number where midterm occurs (optional)

        Returns:
            "pre" or "post" if determinable, None otherwise
        """
        if slide_number is None or midterm_slide is None:
            return None

        if slide_number <= midterm_slide:
            return "pre"
        else:
            return "post"
