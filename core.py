"""作者：Wangyuan；日期：2026-10-29；职责：显式JSON输入的格式、差异和模板预览入口。"""
from typing import Any
from phone import NumberPolicy, normalize
from roster import compare, compare_groups, classify
from templates import build_plan, select_devices, verify_targets


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """仅返回处理结果；不发现名单、不修改源文件、不调用设备。"""
    if not isinstance(payload, dict):
        raise TypeError('输入须为对象')
    action = payload.get('action')
    if action == 'normalize':
        policy = NumberPolicy(**payload['policy'])
        numbers = payload['numbers']
        if not isinstance(numbers, list) or len(numbers) > 5000:
            raise ValueError('numbers须为最多5000项数组')
        rows = [normalize(value, policy) for value in numbers]
        return {'rows': rows, 'valid_count': sum(row['valid'] for row in rows), 'invalid_count': sum(not row['valid'] for row in rows)}
    if action == 'compare':
        return compare(payload['left'], payload['right'], payload.get('strip_parentheses', True))
    if action in ('compare_groups', 'classify'):
        options = {'name_field': payload.get('name_field', 'name'), 'strip_parentheses': payload.get('strip_parentheses', True)}
        if action == 'classify':
            return classify(payload['people'], payload['groups'], group_field=payload.get('group_field', 'groups'), **options)
        return compare_groups(payload['people'], payload['groups'], **options)
    if action == 'plan':
        devices = payload['devices']
        if 'device_keys' in payload:
            devices = select_devices(devices, payload['device_keys'])
        return build_plan(payload['person'], devices, payload['templates'], NumberPolicy(**payload['policy']))
    if action == 'verify_targets':
        return verify_targets(payload['plan'], payload['expected'], payload['allowed_prefixes'])
    raise ValueError('action须为normalize/compare/compare_groups/classify/plan/verify_targets')
