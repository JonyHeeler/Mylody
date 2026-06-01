"""AI 乐评输出校验模块：拦截无证据的高风险事实断言"""

import logging
import re
from dataclasses import fields
from typing import Optional

from mylody.types import ReviewData

logger = logging.getLogger("mylody.ai.guardrails")

HIGH_RISK_PATTERNS = [
    r"发行于\d{4}",
    r"收录于",
    r"制作人[是为]",
    r"由.{1,10}制作",
    r"BPM",
    r"调式",
    r"[大小]调",
    r"采样",
    r"获奖",
    r"Billboard",
    r"格莱美",
    r"排行榜",
    r"写于\d{4}",
    r"创作于\d{4}",
    r"真实经历",
    r"灵感来自",
    r"和声进行",
    r"chord\s*progression",
]

HIGH_RISK_RE = re.compile("|".join(HIGH_RISK_PATTERNS), re.IGNORECASE)

THEME_CLAIM_PATTERNS = [
    r"这[是一首]*.*情歌",
    r"这[是一首]*.*分手歌",
    r"这[是一首]*.*复仇",
    r"写给前任",
    r"写给恋人",
    r"写给爱人",
    r"讲述.*分手",
    r"讲述.*爱情",
    r"讲述.*暗恋",
    r"关于.*背叛",
    r"关于.*失恋",
    r"歌词.*讲",
    r"歌词.*写",
    r"副歌.*唱",
]

THEME_CLAIM_RE = re.compile("|".join(THEME_CLAIM_PATTERNS), re.IGNORECASE)


def normalize_review_payload(data: dict) -> dict:
    """兼容旧版或模型偏离格式的乐评字段"""
    if not isinstance(data, dict):
        return data

    is_compat_shape = "review" in data or any(
        field_name in data
        for field_name in ("summary", "background", "musicology", "why_listen", "similar")
    )
    normalized = dict(data.get("review") or data)
    is_compat_shape = is_compat_shape or any(
        field_name in normalized
        for field_name in ("summary", "background", "musicology", "why_listen", "similar")
    )

    content_parts = []
    for field_name in ("content", "summary", "background", "musicology", "why_listen"):
        value = normalized.get(field_name)
        if isinstance(value, str) and value.strip():
            content_parts.append(value.strip())

    if content_parts:
        normalized["content"] = "\n\n".join(dict.fromkeys(content_parts))

    if "similar_songs" not in normalized and isinstance(normalized.get("similar"), list):
        normalized["similar_songs"] = normalized["similar"]

    if not isinstance(normalized.get("quote"), str) or not normalized.get("quote", "").strip():
        summary = normalized.get("summary")
        if isinstance(summary, str) and summary.strip():
            normalized["quote"] = summary.strip()
        elif isinstance(normalized.get("content"), str):
            normalized["quote"] = _first_sentence(normalized["content"])

    if normalized.get("schema_version") != "review_v2":
        normalized["schema_version"] = "review_v2"

    if is_compat_shape:
        normalized.setdefault("factuality_level", "metadata_only")
        normalized.setdefault("analysis_basis", "track_metadata")
        normalized.setdefault("known_facts", [])
        normalized.setdefault("uncertain_facts", [])
        normalized.setdefault("safety_notes", [])
        normalized.setdefault("evidence_sources", [])

    return normalized


class ValidationResult:
    """校验结果

    Attributes:
        valid: 是否通过校验
        errors: 错误信息列表
        warnings: 警告信息列表
    """

    def __init__(self) -> None:
        self.valid: bool = True
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def add_error(self, message: str) -> None:
        """添加错误

        Args:
            message: 错误描述
        """
        self.valid = False
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """添加警告

        Args:
            message: 警告描述
        """
        self.warnings.append(message)


def validate_review(data: dict) -> ValidationResult:
    """校验 AI 返回的乐评数据

    Args:
        data: AI 返回的原始字典数据

    Returns:
        ValidationResult: 校验结果
    """
    data = normalize_review_payload(data)
    result = ValidationResult()

    if not isinstance(data, dict):
        result.add_error("返回数据不是字典类型")
        return result

    _check_required_fields(data, result)
    _check_types(data, result)
    _check_values(data, result)
    _check_high_risk_content(data, result)
    _check_unsupported_theme_claims(data, result)

    return result


def _check_required_fields(data: dict, result: ValidationResult) -> None:
    """检查必需字段

    Args:
        data: 待校验数据
        result: 校验结果
    """
    required = ["content", "emotion", "similar_songs", "rating"]
    for field_name in required:
        if field_name not in data:
            result.add_error(f"缺少必需字段: {field_name}")


def _check_types(data: dict, result: ValidationResult) -> None:
    """检查字段类型

    Args:
        data: 待校验数据
        result: 校验结果
    """
    if "content" in data and not isinstance(data["content"], str):
        result.add_error("content 必须是字符串")

    if "quote" in data and not isinstance(data["quote"], str):
        result.add_error("quote 必须是字符串")

    if "emotion" in data and not isinstance(data["emotion"], str):
        result.add_error("emotion 必须是字符串")

    if "similar_songs" in data and not isinstance(data["similar_songs"], list):
        result.add_error("similar_songs 必须是列表")

    if "known_facts" in data and not isinstance(data["known_facts"], list):
        result.add_error("known_facts 必须是列表")

    if "uncertain_facts" in data and not isinstance(data["uncertain_facts"], list):
        result.add_error("uncertain_facts 必须是列表")


def _check_values(data: dict, result: ValidationResult) -> None:
    """检查字段值范围

    Args:
        data: 待校验数据
        result: 校验结果
    """
    if "rating" in data:
        rating = data["rating"]
        if not isinstance(rating, (int, float)):
            result.add_error("rating 必须是数字")
        elif rating < 0 or rating > 10:
            result.add_error(f"rating 必须在 0-10 之间，当前值: {rating}")

    if "factuality_level" in data:
        valid_levels = ["metadata_only", "grounded", "mixed"]
        if data["factuality_level"] not in valid_levels:
            result.add_warning(f"factuality_level 值不在预期范围: {data['factuality_level']}")

    if "analysis_basis" in data:
        valid_basis = ["track_metadata", "provided_context", "external_evidence"]
        if data["analysis_basis"] not in valid_basis:
            result.add_warning(f"analysis_basis 值不在预期范围: {data['analysis_basis']}")


def _check_high_risk_content(data: dict, result: ValidationResult) -> None:
    """检查高风险内容（无证据时的事实断言）

    Args:
        data: 待校验数据
        result: 校验结果
    """
    analysis_basis = data.get("analysis_basis", "track_metadata")
    known_facts = data.get("known_facts", [])

    if analysis_basis == "external_evidence" and known_facts:
        return

    content = data.get("content", "")
    matches = HIGH_RISK_RE.findall(content)

    if matches:
        result.add_error(f"检测到无证据的高风险事实断言: {', '.join(set(matches))}")


def _check_unsupported_theme_claims(data: dict, result: ValidationResult) -> None:
    """检查无证据时的歌词主题断言。"""
    analysis_basis = data.get("analysis_basis", "track_metadata")
    known_facts = data.get("known_facts", [])

    if analysis_basis == "external_evidence" and known_facts:
        return

    content = data.get("content", "")
    matches = THEME_CLAIM_RE.findall(content)

    if matches:
        result.add_error(
            f"检测到无证据的歌词主题断言: {', '.join(set(matches))}"
        )


def _first_sentence(text: str) -> str:
    """Extract a short display quote from content."""
    stripped = " ".join(text.split())
    if not stripped:
        return ""
    match = re.search(r"(.{8,80}?[。！？.!?])", stripped)
    if match:
        return match.group(1).strip()
    return stripped[:60].strip()


def validate_and_extract(data: dict) -> Optional[ReviewData]:
    """校验并提取 ReviewData

    Args:
        data: AI 返回的原始字典数据

    Returns:
        Optional[ReviewData]: 校验通过返回 ReviewData，失败返回 None
    """
    data = normalize_review_payload(data)
    result = validate_review(data)

    if result.warnings:
        for warning in result.warnings:
            logger.warning("乐评校验警告: %s", warning)

    if not result.valid:
        for error in result.errors:
            logger.error("乐评校验失败: %s", error)
        return None

    valid_fields = {f.name for f in fields(ReviewData)}
    filtered = {k: v for k, v in data.items() if k in valid_fields}

    try:
        return ReviewData(**filtered)
    except TypeError as e:
        logger.error("构造 ReviewData 失败: %s", e)
        return None
