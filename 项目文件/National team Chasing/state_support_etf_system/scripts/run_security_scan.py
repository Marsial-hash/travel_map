#!/usr/bin/env python3
"""密钥扫描（P7 补丁）：区分变量引用与真实密钥。

- 变量名引用(TUSHARE_TOKEN= / os.getenv) = 允许
- 真实 Token 值出现在 Git 文件/Raw/日志/历史 = CRITICAL
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.adapters.tushare_calendar import get_token  # noqa: E402

# 允许的变量名引用模式（不是真实密钥）
ALLOWLIST_PATTERNS = [
    r"TUSHARE_TOKEN\s*=",  # 赋值
    r'os\.getenv\s*\(\s*["\']TUSHARE_TOKEN["\']',  # 环境变量读取
    r'TUSHARE_TOKEN\s*[\"\']?',  # 文档/配置变量名
]


def is_allowlisted(line: str) -> bool:
    return any(re.search(p, line) for p in ALLOWLIST_PATTERNS)


def scan() -> dict[str, object]:
    token = get_token()
    real_token_value = token or ""
    result: dict[str, object] = {
        "token_variable_reference_count": 0,
        "tracked_real_secret_count": 0,
        "historical_real_secret_count": 0,
        "raw_payload_secret_count": 0,
        "log_secret_count": 0,
        "secret_scan_passed": False,
    }

    # 1) git 文件中的变量引用 + 真实密钥
    REPO_ROOT = Path("/Users/dengyunxuan/Desktop/开发者文件")
    try:
        tracked_raw = subprocess.run(
            ["git", "ls-files", "-z", "项目文件/National team Chasing/state_support_etf_system"],
            cwd=str(REPO_ROOT), capture_output=True, text=True, check=True,
        ).stdout
        # -z 用 NUL 分隔避免 unicode/引号转义问题
        tracked = [p for p in tracked_raw.split("\x00") if p]
    except Exception:
        tracked = []
    for rel in tracked:
        p = REPO_ROOT / rel  # 相对仓库根解析
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        lines = content.splitlines()
        var_refs = sum(1 for ln in lines if "TUSHARE_TOKEN" in ln and is_allowlisted(ln))
        result["token_variable_reference_count"] += var_refs  # type: ignore[operator]
        # 真实密钥值出现在内容中
        if real_token_value and real_token_value in content:
            result["tracked_real_secret_count"] += 1  # type: ignore[operator]

    # 2) git 历史中的真实密钥
    try:
        git_log = subprocess.run(
            ["git", "log", "--all", "-p", "-S", "TUSHARE_TOKEN"],
            cwd="/Users/dengyunxuan/Desktop/开发者文件", capture_output=True, text=True,
        ).stdout
        if real_token_value and real_token_value in git_log:
            result["historical_real_secret_count"] = 1
    except Exception:
        pass

    # 3) Raw payload 中的真实密钥
    raw_dir = PROJECT_ROOT / "warehouse" / "raw"
    if raw_dir.exists():
        for p in raw_dir.rglob("*.json"):
            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                if real_token_value and real_token_value in content:
                    result["raw_payload_secret_count"] += 1  # type: ignore[operator]
            except Exception:
                pass

    # 4) 日志中的真实密钥
    for log in PROJECT_ROOT.rglob("*.log"):
        try:
            content = log.read_text(encoding="utf-8", errors="ignore")
            if real_token_value and real_token_value in content:
                result["log_secret_count"] += 1  # type: ignore[operator]
        except Exception:
            pass

    real_total = (
        int(str(result["tracked_real_secret_count"]))
        + int(str(result["historical_real_secret_count"]))
        + int(str(result["raw_payload_secret_count"]))
        + int(str(result["log_secret_count"]))
    )
    result["secret_scan_passed"] = real_total == 0
    return result


if __name__ == "__main__":
    import json

    r = scan()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    sys.exit(0 if r["secret_scan_passed"] else 1)
