import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Dataset, DatasetRow


MAX_IMPORT_ROWS = 50_000


def json_value(value: Any):
    if value is None or (not isinstance(value, (list, dict)) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def infer_columns(frame: pd.DataFrame) -> list[dict]:
    result = []
    for name in frame.columns:
        series = frame[name]
        non_null = series.dropna()
        if pd.api.types.is_numeric_dtype(series):
            kind = "number"
        elif pd.api.types.is_datetime64_any_dtype(series):
            kind = "datetime"
        else:
            numeric = pd.to_numeric(non_null, errors="coerce") if len(non_null) else pd.Series(dtype=float)
            kind = "number" if len(non_null) and numeric.notna().mean() >= 0.9 else "category"
        result.append({"name": str(name), "type": kind, "nulls": int(series.isna().sum()), "unique": int(non_null.nunique())})
    return result


def create_dataset(db: Session, user_id: int, name: str, frame: pd.DataFrame, source_type: str, source_label: str | None = None) -> Dataset:
    if frame.empty:
        raise HTTPException(400, "The source contains no rows.")
    if len(frame) > MAX_IMPORT_ROWS:
        raise HTTPException(413, f"Imports are limited to {MAX_IMPORT_ROWS:,} rows per dataset.")
    frame = frame.copy()
    frame.columns = [str(column).strip() or f"column_{index + 1}" for index, column in enumerate(frame.columns)]
    if len(set(frame.columns)) != len(frame.columns):
        raise HTTPException(400, "Column names must be unique.")
    columns = infer_columns(frame)
    dataset = Dataset(user_id=user_id, name=name.strip(), source_type=source_type, source_label=source_label, columns=columns, row_count=len(frame))
    db.add(dataset)
    db.flush()
    records = frame.to_dict(orient="records")
    db.add_all([DatasetRow(dataset_id=dataset.id, position=index, payload={str(k): json_value(v) for k, v in row.items()}) for index, row in enumerate(records)])
    db.commit()
    db.refresh(dataset)
    return dataset


def owned_dataset(db: Session, dataset_id: int, user_id: int) -> Dataset:
    dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id, Dataset.user_id == user_id))
    if not dataset:
        raise HTTPException(404, "Dataset not found.")
    return dataset


def dataframe(db: Session, dataset: Dataset) -> pd.DataFrame:
    rows = db.scalars(select(DatasetRow).where(DatasetRow.dataset_id == dataset.id).order_by(DatasetRow.position)).all()
    frame = pd.DataFrame([row.payload for row in rows], columns=[column["name"] for column in dataset.columns])
    for column in dataset.columns:
        if column["type"] == "number":
            frame[column["name"]] = pd.to_numeric(frame[column["name"]], errors="coerce")
    return frame


def dataset_summary(frame: pd.DataFrame, columns: list[dict]) -> dict:
    numeric = [column["name"] for column in columns if column["type"] == "number"]
    categorical = [column["name"] for column in columns if column["type"] == "category"]
    metrics = []
    for name in numeric[:6]:
        series = pd.to_numeric(frame[name], errors="coerce").dropna()
        if len(series):
            metrics.append({"column": name, "sum": json_value(series.sum()), "average": json_value(series.mean()), "min": json_value(series.min()), "max": json_value(series.max())})
    return {"rows": len(frame), "columns": len(columns), "numeric_columns": len(numeric), "category_columns": len(categorical), "metrics": metrics}


def chart_data(
    frame: pd.DataFrame,
    category: str | None,
    value: str,
    aggregation: str = "sum",
    limit: int = 12,
    chart_type: str = "bar",
) -> dict:
    if chart_type not in {"bar", "line"}:
        raise HTTPException(400, "Chart type must be bar or line.")
    if value not in frame.columns:
        raise HTTPException(400, "Unknown value column.")
    values = pd.to_numeric(frame[value], errors="coerce")
    if category:
        if category not in frame.columns:
            raise HTTPException(400, "Unknown category column.")
        work = pd.DataFrame({"category": frame[category].fillna("Unknown").astype(str), "value": values}).dropna(subset=["value"])
        grouped = work.groupby("category", dropna=False, sort=False)["value"]
        operations = {"sum": grouped.sum, "mean": grouped.mean, "count": grouped.count, "min": grouped.min, "max": grouped.max}
        if aggregation not in operations:
            raise HTTPException(400, "Aggregation must be sum, mean, count, min, or max.")
        result = operations[aggregation]()
        if chart_type == "bar":
            result = result.sort_values(ascending=False)
        result = result.head(min(limit, 50))
        labels, data = result.index.tolist(), [json_value(v) for v in result.tolist()]
    else:
        clean = values.dropna()
        labels = [value]
        operations = {"sum": clean.sum, "mean": clean.mean, "count": clean.count, "min": clean.min, "max": clean.max}
        if aggregation not in operations:
            raise HTTPException(400, "Invalid aggregation.")
        data = [json_value(operations[aggregation]())]
    resolved_type = chart_type if category else "number"
    return {"type": resolved_type, "title": f"{aggregation.title()} of {value}" + (f" by {category}" if category else ""), "labels": labels, "series": [{"name": value, "values": data}], "category": category, "value": value, "aggregation": aggregation}


def profile_for_ai(frame: pd.DataFrame, columns: list[dict]) -> dict:
    profile = {"row_count": len(frame), "columns": columns, "statistics": {}, "sample": []}
    for column in columns:
        name = column["name"]
        series = frame[name]
        if column["type"] == "number":
            clean = pd.to_numeric(series, errors="coerce").dropna()
            if len(clean):
                profile["statistics"][name] = {"min": json_value(clean.min()), "max": json_value(clean.max()), "mean": json_value(clean.mean()), "sum": json_value(clean.sum())}
        else:
            profile["statistics"][name] = {"top_values": {str(k): int(v) for k, v in series.fillna("Unknown").astype(str).value_counts().head(8).items()}}
    profile["sample"] = [{k: json_value(v) for k, v in row.items()} for row in frame.head(8).to_dict(orient="records")]
    return profile
