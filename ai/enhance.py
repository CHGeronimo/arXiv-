import os
import json
import sys
import re
import signal
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
from queue import Queue
from threading import Lock
from datetime import datetime
# INSERT_YOUR_CODE
import requests

import dotenv
import argparse
from tqdm import tqdm

import langchain_core.exceptions
from langchain_openai import ChatOpenAI
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from .structure import Structure

_AI_DIR = os.path.dirname(os.path.abspath(__file__))

_env_path = os.path.join(_AI_DIR, '.env')
if os.path.exists(_env_path):
    dotenv.load_dotenv(_env_path)
template = open(os.path.join(_AI_DIR, "template.txt"), "r").read()
system = open(os.path.join(_AI_DIR, "system.txt"), "r").read()


def load_research_profile() -> dict:
    profile_path = os.path.join(os.path.dirname(__file__), '..', 'research_profile.json')
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            return json.load(f)
    return {"direction": "", "keywords": [], "quality_criteria": ""}


def build_chain(model_name: str):
    llm = ChatOpenAI(model=model_name).with_structured_output(Structure, method="json_mode")
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system),
        HumanMessagePromptTemplate.from_template(template=template)
    ])
    return prompt_template | llm


def enhance_single(paper: dict, chain, profile: dict, language: str) -> dict | None:
    default_ai = {
        "tldr": "", "motivation": "", "method": "", "result": "", "conclusion": "",
        "title_zh": "", "summary_zh": "",
        "quality_score": 0, "relevance_score": 0, "recommendation": "skip",
    }
    try:
        response: Structure = chain.invoke({
            "language": language,
            "content": paper.get("summary", ""),
            "title": paper.get("title", ""),
            "research_direction": profile.get("direction", ""),
            "keywords": ", ".join(profile.get("keywords", [])),
        })
        paper["AI"] = response.model_dump()
    except langchain_core.exceptions.OutputParserException as e:
        error_msg = str(e)
        partial = {}
        try:
            if "Function Structure arguments:" in error_msg:
                json_str = error_msg.split("Function Structure arguments:", 1)[1].strip().split("are not valid JSON")[0].strip()
            else:
                start = error_msg.find('{')
                end = error_msg.rfind('}')
                if start != -1 and end != -1:
                    json_str = error_msg[start:end+1]
                else:
                    json_str = ""
            if json_str:
                partial = json.loads(json_str)
        except Exception:
            pass
        paper["AI"] = {**default_ai, **partial}
    except Exception as e:
        logger.error(f"Enhance error for {paper.get('id','?')}: {e}")
        paper["AI"] = default_ai
    for k in default_ai:
        if k not in paper["AI"]:
            paper["AI"][k] = default_ai[k]
    return paper


logger = logging.getLogger(__name__)

# Ctrl+C 中断标志
_shutdown = False


def _signal_handler(signum, frame):
    global _shutdown
    if _shutdown:
        logger.warning("强制退出...")
        sys.exit(1)
    _shutdown = True
    logger.warning("收到中断信号，正在保存已处理的结果... (再按一次强制退出)")


class _FlushFileHandler(logging.FileHandler):
    """每次写入后立即 flush，确保 tail -f 实时可见"""
    def emit(self, record):
        super().emit(record)
        self.flush()


def setup_logging() -> None:
    """配置日志：同时输出到控制台和日志文件（实时刷新）"""
    log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stderr),
            _FlushFileHandler(log_file, encoding='utf-8'),
        ],
    )
    logger.info(f"日志文件: {log_file}")

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    parser.add_argument("--max_workers", type=int, default=1, help="Maximum number of parallel workers")
    parser.add_argument("--existing", type=str, default=None, help="existing enhanced file to skip processed IDs")
    return parser.parse_args()

def process_single_item(chain, item: Dict, language: str) -> Dict:
    # 敏感词检测服务状态缓存
    _sensitive_service_down = False

    def is_sensitive(content: str) -> bool:
        nonlocal _sensitive_service_down
        if _sensitive_service_down:
            return False
        try:
            resp = requests.post(
                "https://spam.dw-dengwei.workers.dev",
                json={"text": content},
                timeout=3
            )
            if resp.status_code == 200:
                result = resp.json()
                return result.get("sensitive", True)
            else:
                return False
        except Exception:
            _sensitive_service_down = True
            logger.warning("敏感词检测服务不可达，后续跳过检查")
            return False

    def check_github_code(content: str) -> Dict:
        """提取并验证 GitHub 链接"""
        code_info = {}

        github_pattern = r"https?://github\.com/([a-zA-Z0-9-_]+)/([a-zA-Z0-9-_\.]+)"
        match = re.search(github_pattern, content)

        if match:
            owner, repo = match.groups()
            repo = repo.rstrip(".git").rstrip(".,)")

            full_url = f"https://github.com/{owner}/{repo}"
            code_info["code_url"] = full_url

            github_token = os.environ.get("TOKEN_GITHUB")
            headers = {"Accept": "application/vnd.github.v3+json"}
            if github_token:
                headers["Authorization"] = f"token {github_token}"

            try:
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                resp = requests.get(api_url, headers=headers, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    code_info["code_stars"] = data.get("stargazers_count", 0)
                    code_info["code_last_update"] = data.get("pushed_at", "")[:10]
            except Exception:
                pass
            return code_info

        github_io_pattern = r"https?://[a-zA-Z0-9-_]+\.github\.io(?:/[a-zA-Z0-9-_\.]+)*"
        match_io = re.search(github_io_pattern, content)

        if match_io:
            url = match_io.group(0)
            url = url.rstrip(".,)")
            code_info["code_url"] = url

        return code_info

    # 检查 summary 字段
    if is_sensitive(item.get("summary", "")):
        return None

    # 检测代码可用性
    code_info = check_github_code(item.get("summary", ""))
    if code_info:
        item.update(code_info)

    """处理单个数据项"""
    # Default structure with meaningful fallback values
    default_ai_fields = {
        "tldr": "Summary generation failed",
        "motivation": "Motivation analysis unavailable",
        "method": "Method extraction failed",
        "result": "Result analysis unavailable",
        "conclusion": "Conclusion extraction failed",
        "title_zh": "Translation failed",
        "summary_zh": "Translation failed"
    }

    try:
        response: Structure = chain.invoke({
            "language": language,
            "content": item.get('summary', ''),
            "title": item.get('title', ''),
            "research_direction": "",
            "keywords": "",
        })
        item['AI'] = response.model_dump()
    except langchain_core.exceptions.OutputParserException as e:
        error_msg = str(e)
        partial_data = {}

        logger.debug(f"OutputParserException for {item.get('id', 'unknown')}: {error_msg[:500]}")

        try:
            if "Function Structure arguments:" in error_msg:
                json_str = error_msg.split("Function Structure arguments:", 1)[1].strip().split('are not valid JSON')[0].strip()
            else:
                start = error_msg.find('{')
                end = error_msg.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = error_msg[start:end+1]
                else:
                    json_str = ""

            if json_str:
                partial_data = json.loads(json_str)
        except Exception as json_e:
            logger.warning(f"Failed to parse JSON for {item.get('id', 'unknown')}: {json_e}")

        item['AI'] = {**default_ai_fields, **partial_data}
        logger.warning(f"Using partial AI data for {item.get('id', 'unknown')}: {list(partial_data.keys())}")
    except Exception as e:
        logger.error(f"Unexpected error for {item.get('id', 'unknown')}: {e}")
        item['AI'] = default_ai_fields

    for field in default_ai_fields.keys():
        if field not in item['AI']:
            item['AI'][field] = default_ai_fields[field]

    for v in item.get("AI", {}).values():
        if is_sensitive(str(v)):
            return None
    return item

def _process_item_and_write(chain, item: Dict, language: str, f, saved_count: int) -> int:
    """处理单篇论文并写入文件，返回更新后的 saved_count"""
    default_ai_fields = {
        "tldr": "Summary generation failed",
        "motivation": "Motivation analysis unavailable",
        "method": "Method extraction failed",
        "result": "Result analysis unavailable",
        "conclusion": "Conclusion extraction failed",
        "title_zh": "Translation failed",
        "summary_zh": "Translation failed"
    }
    try:
        result = process_single_item(chain, item, language, f, saved_count)
        if result is not None:
            f.write(json.dumps(result) + "\n")
            f.flush()
            return saved_count + 1
    except Exception as e:
        logger.error(f"Item {item.get('id', 'unknown')} exception: {e}")
        item['AI'] = default_ai_fields
        f.write(json.dumps(item) + "\n")
        f.flush()
        return saved_count + 1
    return saved_count


def process_all_items(data: List[Dict], model_name: str, language: str, max_workers: int,
                      output_file: str, existing_count: int) -> int:
    """处理所有数据项，每完成一篇立即追加到文件"""
    global _shutdown
    chain = build_chain(model_name)
    logger.info(f"Connect to: {model_name}")
    saved_count = 0
    pbar = tqdm(total=len(data), desc="AI 增强处理", unit="篇", ncols=100)

    try:
        with open(output_file, "a") as f:
            if max_workers <= 1:
                for item in data:
                    if _shutdown:
                        break
                    saved_count = _process_item_and_write(chain, item, language, f, saved_count)
                    pbar.update(1)
                    pbar.set_postfix(已存=existing_count + saved_count)
            else:
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_item = {
                        executor.submit(process_single_item, chain, item, language): (idx, item)
                        for idx, item in enumerate(data)
                    }
                    for future in as_completed(future_to_item):
                        if _shutdown:
                            break
                        idx, item = future_to_item[future]
                        try:
                            result = future.result()
                            if result is not None:
                                f.write(json.dumps(result) + "\n")
                                f.flush()
                                saved_count += 1
                        except Exception as e:
                            logger.error(f"Item {idx} exception: {e}")
                            item['AI'] = {
                                "tldr": "Processing failed",
                                "motivation": "Processing failed",
                                "method": "Processing failed",
                                "result": "Processing failed",
                                "conclusion": "Processing failed"
                            }
                            f.write(json.dumps(item) + "\n")
                            f.flush()
                            saved_count += 1
                        pbar.update(1)
                        pbar.set_postfix(已存=existing_count + saved_count)
    except KeyboardInterrupt:
        _shutdown = True
        logger.warning(f"Ctrl+C 中断: 已存 {saved_count}/{len(data)} 篇")
    pbar.close()
    return saved_count

def main():
    global _shutdown
    signal.signal(signal.SIGINT, _signal_handler)

    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", 'deepseek-v4-flash')
    language = os.environ.get("LANGUAGE", 'Chinese')

    # 目标文件路径
    target_file = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')

    logger.info(f"读取数据: {args.data}")

    # 读取数据
    data = []
    with open(args.data, "r") as f:
        for line in f:
            data.append(json.loads(line))

    # 去重
    seen_ids = set()
    unique_data = []
    for item in data:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)

    # 增量模式：跳过已处理的论文
    existing_data = []
    existing_ids = set()
    if os.path.exists(target_file):
        with open(target_file, "r") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    existing_data.append(item)
                    existing_ids.add(item['id'])
        logger.info(f"增量模式：已有 {len(existing_ids)} 篇增强结果")

    new_data = [item for item in unique_data if item['id'] not in existing_ids]
    logger.info(f"需要处理: {len(new_data)} 篇 (跳过 {len(unique_data) - len(new_data)} 篇已有)")

    if not new_data:
        logger.info("无新论文需要处理")
        return

    # 先将已有数据写入文件（覆盖旧文件）
    with open(target_file, "w") as f:
        for item in existing_data:
            f.write(json.dumps(item) + "\n")
    logger.info(f"已写入 {len(existing_data)} 篇已有结果到 {target_file}")

    # 流式处理：每完成一篇立即追加到文件
    saved_count = process_all_items(
        new_data,
        model_name,
        language,
        args.max_workers,
        target_file,
        len(existing_data),
    )

    total = len(existing_data) + saved_count
    if _shutdown:
        logger.warning(f"中断保存: {target_file} ({total} 篇)")
    else:
        logger.info(f"保存完成: {target_file} ({total} 篇，含已有 {len(existing_data)} 篇)")

if __name__ == "__main__":
    setup_logging()
    main()
