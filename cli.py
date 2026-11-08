"""作者：Wangyuan；日期：2026-10-29；职责：显式JSON文件的离线CLI与不覆盖输出。"""
import argparse
import json
from pathlib import Path
import sys
from core import run


def main() -> int:
    """有界读取、标准JSON输出；错误返回2且不打印调用栈。"""
    parser = argparse.ArgumentParser(description='显式联系信息转换：格式/名单差异/模板预览')
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        with args.input.open('rb') as handle:
            content = handle.read(1024 * 1024 + 1)
        if len(content) > 1024 * 1024:
            raise ValueError('输入不能超过1MiB')
        def reject_constant(value: str) -> None:
            raise ValueError('输入不能含NaN/Infinity')
        payload = json.loads(content, parse_constant=reject_constant)
        result = json.dumps(run(payload), ensure_ascii=False, indent=2, allow_nan=False) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as handle:
                handle.write(result)
        else:
            sys.stdout.write(result)
        return 0
    except (ValueError, TypeError, KeyError, OSError, OverflowError, RecursionError) as exc:
        print(f'失败：{type(exc).__name__}: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
