from __future__ import annotations

import re

from invstruct.ocr.base import OcrTextBlock
from invstruct.schemas import FieldProvenance
from invstruct.templates.models import TemplateSpec

FieldCandidate = tuple[str, float, FieldProvenance]


def _anchor_neighbor(anchor: OcrTextBlock, blocks: list[OcrTextBlock], direction: str) -> OcrTextBlock | None:
    ax1, ay1, ax2, ay2 = anchor.bbox if len(anchor.bbox) == 4 else [0.0, 0.0, 0.0, 0.0]
    candidates: list[tuple[float, OcrTextBlock]] = []
    for block in blocks:
        if block is anchor or len(block.bbox) != 4:
            continue
        bx1, by1, bx2, by2 = block.bbox
        is_right = bx1 >= ax2 and abs(by1 - ay1) < 80
        is_below = by1 >= ay2 and abs(bx1 - ax1) < 120
        if direction == "right" and not is_right:
            continue
        if direction == "below" and not is_below:
            continue
        if direction == "right_or_below" and not (is_right or is_below):
            continue
        distance = abs(bx1 - ax2) + abs(by1 - ay2)
        candidates.append((distance, block))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0])
    return candidates[0][1]


def extract_fields_with_template(blocks: list[OcrTextBlock], template: TemplateSpec) -> dict[str, FieldCandidate]:
    results: dict[str, FieldCandidate] = {}

    for field_name, aliases in template.aliases.items():
        pattern = template.regex.get(field_name)
        anchor_rule = template.anchors.get(field_name)
        best: FieldCandidate | None = None

        for line_id, block in enumerate(blocks):
            text = block.text.strip()
            if not text:
                continue

            matched_alias = any(alias.lower() in text.lower() for alias in aliases)
            if not matched_alias and not pattern:
                continue

            candidate_text = text
            layout_score = 0.0
            if anchor_rule and any(keyword.lower() in text.lower() for keyword in anchor_rule.keywords):
                neighbor = _anchor_neighbor(block, blocks, anchor_rule.direction)
                if neighbor is not None:
                    candidate_text = neighbor.text.strip()
                    layout_score = 1.0

            regex_score = 0.0
            if pattern:
                match = re.search(pattern, candidate_text)
                if match:
                    candidate_text = match.group(1) if match.groups() else match.group(0)
                    regex_score = 1.0
                elif matched_alias:
                    continue

            ocr_component = block.conf * template.scoring.ocr_conf_weight
            regex_component = regex_score * template.scoring.regex_weight
            layout_component = layout_score * template.scoring.layout_weight
            total_score = min(1.0, ocr_component + regex_component + layout_component)

            provenance = FieldProvenance(
                page=block.page,
                bbox=block.bbox,
                extractor=f"template:{template.template_id}",
                line_id=line_id,
                line_text=candidate_text or block.text,
            )
            candidate = (candidate_text, total_score, provenance)
            if best is None or candidate[1] > best[1]:
                best = candidate

        if best is not None:
            results[field_name] = best

    return results
