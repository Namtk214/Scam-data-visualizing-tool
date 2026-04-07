"""
io_utils.py — Load file JSON/JSONL/CSV và parse từ Streamlit uploader.
"""
import json
import io
import csv
from typing import List, Dict, Any, Optional


def load_json(path: str) -> List[Dict[str, Any]]:
    """Load file JSON — hỗ trợ cả list hoặc single object."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return [data]


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    """Load file JSONL — mỗi dòng là 1 JSON object."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_csv(path: str) -> List[Dict[str, Any]]:
    """Load CSV cơ bản — mỗi row là 1 dict."""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(dict(row))
    return records


def parse_uploaded_file(uploaded_file) -> List[Dict[str, Any]]:
    """
    Parse Streamlit UploadedFile object.
    Hỗ trợ .json, .jsonl, .csv.
    """
    filename = uploaded_file.name.lower()
    content = uploaded_file.read()

    if filename.endswith(".jsonl"):
        return _parse_jsonl_bytes(content)
    elif filename.endswith(".json"):
        return _parse_json_bytes(content)
    elif filename.endswith(".csv"):
        return _parse_csv_bytes(content)
    else:
        raise ValueError(f"Unsupported file type: {filename}")


def _parse_json_bytes(content: bytes) -> List[Dict[str, Any]]:
    text = content.decode("utf-8")
    data = json.loads(text)
    if isinstance(data, list):
        return data
    return [data]


def _parse_jsonl_bytes(content: bytes) -> List[Dict[str, Any]]:
    text = content.decode("utf-8")
    records = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _parse_csv_bytes(content: bytes) -> List[Dict[str, Any]]:
    text = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(row) for row in reader]


def parse_raw_json_text(text: str) -> List[Dict[str, Any]]:
    """Parse JSON text được paste trực tiếp vào textbox."""
    data = json.loads(text)
    if isinstance(data, list):
        return data
    return [data]
