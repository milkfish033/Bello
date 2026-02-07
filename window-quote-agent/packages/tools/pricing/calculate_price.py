"""
定价计算：基于 price.json 定价标准，按
  BasePrice(model) × AreaFactor(width×height) × PanelFactor(panel_count) × TypeFactor(窗/推拉门/Lift-slide)
计算。缺失的 AreaFactor / PanelFactor / TypeFactor 按最小值计。
"""
from pathlib import Path
from typing import Any

# 尺寸：requirements 为米，price.json 为 inch
METER_TO_INCH = 39.3701

# 产品类型与 TypeFactor（缺失按最小=1.0）
TYPE_FACTORS = {
    "窗": 1.0,
    "推拉门": 1.0,
    "Lift-slide": 1.0,
}

# series_id（推荐节点常用）-> price.json 中的 model，便于查价
SERIES_ID_TO_MODEL: dict[str, str] = {
    "65": "ROW100P",
    "70": "RC2",
    "80": "RW80",
    "120": "ROW120E",
    "130": "ROW130F",
    "113": "RSW113P",
    "140": "RSW140P",
    "125": "RSD125P",
    "185": "RSD185P",
    "100": "HD100B",
    "70B": "RFD70",
    "80D": "RD80",
}

# category -> 类型键
CATEGORY_TO_TYPE = {
    "casement_window": "窗",
    "security_window": "窗",
    "parallel_outward_window": "窗",
    "inswing_window": "窗",
    "vent_window": "窗",
    "sliding_window": "窗",
    "sliding_door": "推拉门",
    "bifold_door": "推拉门",
    "hinged_door": "推拉门",
    "lift_slide_door": "Lift-slide",
}


def _price_json_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "price" / "reference" / "price.json"


def _load_pricing_data() -> dict[str, Any]:
    path = _price_json_path()
    if not path.exists():
        return {"models": []}
    import json
    return json.loads(path.read_text(encoding="utf-8"))


def _find_model(data: dict[str, Any], model_id: str) -> dict[str, Any] | None:
    model_id = (model_id or "").strip()
    if not model_id:
        return None
    for m in data.get("models") or []:
        if (m.get("model") or "").strip() == model_id:
            return m
    return None


def _midpoint(r: Any) -> float | None:
    if isinstance(r, (list, tuple)) and len(r) >= 2:
        return (float(r[0]) + float(r[1])) / 2.0
    return None


def _base_price_for_model(model: dict[str, Any]) -> float:
    """BasePrice(model)：基准价，取 1_panel 或 single_door 或首个键的中位价。"""
    base_range = model.get("base_price_range") or {}
    for key in ("1_panel", "single_door"):
        if key in base_range:
            m = _midpoint(base_range[key])
            if m is not None:
                return m
    for v in base_range.values():
        m = _midpoint(v)
        if m is not None:
            return m
    return 0.0


def _panel_factor_from_base_range(model: dict[str, Any], panel_count: int) -> float:
    """PanelFactor(panel_count)：相对基准价的系数；缺失按最小 1.0。"""
    base_range = model.get("base_price_range") or {}
    base_mid = None
    for key in ("1_panel", "single_door"):
        if key in base_range:
            base_mid = _midpoint(base_range[key])
            break
    if base_mid is None:
        for v in base_range.values():
            base_mid = _midpoint(v)
            if base_mid is not None:
                break
    if base_mid is None or base_mid <= 0:
        return 1.0
    panel_key = f"{panel_count}_panel"
    if panel_key in base_range:
        m = _midpoint(base_range[panel_key])
        if m is not None:
            return m / base_mid
    if panel_count == 2 and "double_door" in base_range:
        m = _midpoint(base_range["double_door"])
        if m is not None:
            return m / base_mid
    return 1.0


def _area_factor_for_model(model: dict[str, Any], width_m: float, height_m: float) -> float:
    """AreaFactor(width×height)：按 size_tiers 匹配宽高(英寸)，取 multiplier；缺失取最小。"""
    w_inch = width_m * METER_TO_INCH
    h_inch = height_m * METER_TO_INCH
    tiers = model.get("size_tiers") or []
    for t in tiers:
        wr = t.get("width_range") or []
        hr = t.get("height_range") or []
        if len(wr) >= 2 and len(hr) >= 2:
            if wr[0] <= w_inch <= wr[1] and hr[0] <= h_inch <= hr[1]:
                return float(t.get("multiplier", 1.0))
    # 缺失按最小
    if tiers:
        return min(float(t.get("multiplier", 1.0)) for t in tiers)
    return 1.0


def _type_factor_for_model(model: dict[str, Any]) -> float:
    """TypeFactor(窗/推拉门/Lift-slide)：按 category 映射；缺失按最小 1.0。"""
    cat = (model.get("category") or "").strip()
    type_key = CATEGORY_TO_TYPE.get(cat)
    if type_key and type_key in TYPE_FACTORS:
        return TYPE_FACTORS[type_key]
    return min(TYPE_FACTORS.values())  # 1.0


def calculate_price(requirements: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    """
    根据 requirements（w/h 米、opening_count 等）与 selection（series_id/model）查 price.json，
    计算：BasePrice(model) × AreaFactor(w×h) × PanelFactor(panel_count) × TypeFactor(type)。
    缺失的 AreaFactor/PanelFactor/TypeFactor 按最小算。
    返回 price_result：total, breakdown, series_id/model 等。
    """
    data = _load_pricing_data()
    raw_id = (selection.get("model") or selection.get("series_id") or "").strip()
    model_id = raw_id
    if not _find_model(data, model_id):
        model_id = SERIES_ID_TO_MODEL.get(raw_id, raw_id)
    model = _find_model(data, model_id) if model_id else None
    if not model:
        return {
            "total": 0.0,
            "breakdown": [],
            "series_id": raw_id,
            "error": "未找到定价型号",
        }

    w = float(requirements.get("w") or 0)
    h = float(requirements.get("h") or 0)
    panel_count = int(requirements.get("opening_count") or selection.get("panel_count") or 1)
    if panel_count < 1:
        panel_count = 1

    base = _base_price_for_model(model)
    area_factor = _area_factor_for_model(model, w, h) if w > 0 and h > 0 else min(
        float(t.get("multiplier", 1.0)) for t in (model.get("size_tiers") or [{"multiplier": 1.0}])
    )
    panel_factor = _panel_factor_from_base_range(model, panel_count)
    type_factor = _type_factor_for_model(model)

    total = base * area_factor * panel_factor * type_factor
    area = w * h

    # 报价单展示：面积 × 综合单价
    unit_price = round(total / area, 2) if area > 0 else 0
    breakdown_display = [
        {"item": "窗面积(㎡)", "qty": round(area, 4), "unit_price": unit_price, "amount": round(total, 2)},
    ]

    return {
        "total": round(total, 2),
        "breakdown": breakdown_display,
        "series_id": raw_id,
        "model": model.get("model", ""),
        "base_price": round(base, 2),
        "area_factor": round(area_factor, 4),
        "panel_factor": round(panel_factor, 4),
        "type_factor": round(type_factor, 4),
    }
