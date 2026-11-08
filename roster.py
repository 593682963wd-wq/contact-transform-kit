"""作者：Wangyuan；日期：2026-10-29；职责：显式名单差异、歧义检测与分组候选。"""
from collections import defaultdict
from copy import deepcopy
import re
import unicodedata
from typing import Any


def name_key(name: str, strip_parentheses: bool = True) -> str:
    """可选去括号标签并统一Unicode；不作同音、模糊或人员身份推断。"""
    if not isinstance(name, str) or not 1 <= len(name) <= 120:
        raise ValueError('姓名/标签须为1至120字符文本')
    if type(strip_parentheses) is not bool:
        raise ValueError('strip_parentheses须为布尔值')
    key = unicodedata.normalize('NFC', name).strip()
    if strip_parentheses:
        previous = None
        while previous != key:
            previous = key
            key = re.sub(r'\([^()]*\)|（[^（）]*）', '', key)
    key = ' '.join(key.split())
    if not key:
        raise ValueError('姓名归一化后为空')
    return key


def names(value: Any) -> list[str]:
    """支持显式字符串列表或逗号/分号/换行分隔文本，保留名字内部空格。"""
    if isinstance(value, str):
        value = [x.strip() for x in re.split(r'[,，、;；\n]+', value) if x.strip()]
    if not isinstance(value, list) or len(value) > 5000 or any(not isinstance(x, str) for x in value):
        raise ValueError('名单须为最多5000项的文本数组或分隔文本')
    for name in value:
        name_key(name, False)
    return list(value)


def _index(values: Any, strip_parentheses: bool) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    for value in names(values):
        result[name_key(value, strip_parentheses)].append(value)
    return dict(result)


def compare(left: Any, right: Any, strip_parentheses: bool = True) -> dict[str, Any]:
    """集合差异保留原显示值；重复归一化键单列歧义，不静默覆盖。"""
    a, b = _index(left, strip_parentheses), _index(right, strip_parentheses)
    keys = sorted(set(a) | set(b))
    ambiguous = [key for key in keys if len(a.get(key, [])) > 1 or len(b.get(key, [])) > 1]
    return {
        'matched': [{'key': key, 'left': a[key][0], 'right': b[key][0]}
                    for key in keys if key in a and key in b and key not in ambiguous],
        'only_left': [name for key in keys if key not in b for name in a[key]],
        'only_right': [name for key in keys if key not in a for name in b[key]],
        'ambiguous': [{'key': key, 'left': a.get(key, []), 'right': b.get(key, [])} for key in ambiguous],
        'left_unique': len(a), 'right_unique': len(b), 'state': 'candidate_comparison',
    }


def compare_groups(people: list[dict[str, Any]], groups: dict[str, Any],
                   name_field: str = 'name', strip_parentheses: bool = True) -> dict[str, Any]:
    """统计每组差异与跨组归属候选；有同名歧义时不自动归属。"""
    if not isinstance(people, list) or len(people) > 5000 or any(not isinstance(p, dict) for p in people):
        raise ValueError('people须为最多5000项的对象数组')
    if not isinstance(groups, dict) or len(groups) > 100:
        raise ValueError('groups须为最多100项的对象')
    left = [p[name_field] for p in people]
    table = _index(left, strip_parentheses)
    indices, per_group = {}, {}
    for label, entries in groups.items():
        name_key(label, False)
        indices[label] = _index(entries, strip_parentheses)
        comparison = compare(left, entries, strip_parentheses)
        per_group[label] = {'count': len(indices[label]), 'matched': comparison['matched'],
                            'missing_in_table': comparison['only_right'], 'ambiguous': comparison['ambiguous']}
    classified = []
    for person in people:
        key = name_key(person[name_field], strip_parentheses)
        matches = [label for label, index in indices.items() if key in index]
        ambiguous = len(table[key]) > 1 or any(len(indices[label][key]) > 1 for label in matches)
        classified.append({'name': person[name_field], 'groups': [] if ambiguous else matches,
                           'candidate_groups': matches, 'ambiguous': ambiguous})
    return {'per_group': per_group, 'classified': classified,
            'extra_in_table': [p['name'] for p in classified if not p['candidate_groups']],
            'state': 'candidate_classification'}


def classify(people: list[dict[str, Any]], groups: dict[str, Any], name_field: str = 'name',
             group_field: str = 'groups', strip_parentheses: bool = True) -> dict[str, Any]:
    """生成不修改原对象的分类副本；不写入名册、不宣布正式人员归属。"""
    if not isinstance(group_field, str) or not group_field or group_field == name_field:
        raise ValueError('group_field须独立于name_field')
    comparison = compare_groups(people, groups, name_field, strip_parentheses)
    copies = deepcopy(people)
    for row, membership in zip(copies, comparison['classified']):
        row[group_field] = membership['groups']
    return {'people': copies, 'comparison': comparison, 'state': 'candidate_only'}
