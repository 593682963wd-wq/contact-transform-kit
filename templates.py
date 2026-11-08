"""作者：Wangyuan；日期：2026-10-29；职责：显式模板的本地计划预览，不拨号或发送。"""
import re
from string import Formatter
from typing import Any
from phone import NumberPolicy, normalize


def label(value: Any) -> str:
    """设备、类别和变体名称须是有界文本。"""
    if not isinstance(value, str) or not value.strip() or len(value) > 100:
        raise ValueError('标签须为1至100字符')
    return value


def select_devices(devices: list[dict[str, Any]], keys: list[str]) -> list[dict[str, Any]]:
    """按给定顺序选择设备；重复标识和未知标识明确失败。"""
    if not isinstance(devices, list) or len(devices) > 100 or any(not isinstance(d, dict) for d in devices):
        raise ValueError('devices须为最多100项对象数组')
    if not isinstance(keys, list) or len(keys) > 100:
        raise ValueError('keys须为最多100项数组')
    index = {}
    for device in devices:
        key = label(device['key'])
        if key in index:
            raise ValueError('设备key重复')
        index[key] = device
    checked = [label(key) for key in keys]
    if len(set(checked)) != len(checked):
        raise ValueError('所选key重复')
    if any(key not in index for key in checked):
        raise ValueError('存在未配置的设备key')
    return [dict(index[key]) for key in checked]


def render_template(template: str, values: dict[str, str], require_target: bool = False) -> str:
    """只替换白名单字面占位符，拒绝属性访问、格式指令和转换器。"""
    if not isinstance(template, str) or not template or len(template) > 256:
        raise ValueError('template须为1至256字符')
    fields = []
    for _, field, spec, conversion in Formatter().parse(template):
        if field is not None:
            if field not in values or spec or conversion:
                raise ValueError('模板只允许target/device_key/label字面占位符')
            fields.append(field)
    if require_target and fields.count('target') != 1:
        raise ValueError('目标模板必须且只能包含一次{target}')
    return template.format_map(values)


def build_plan(person: dict[str, Any], devices: list[dict[str, Any]],
               templates: dict[str, Any], policy: NumberPolicy) -> dict[str, Any]:
    """按明确选择的变体或全部候选变体生成计划；没有默认运营商命令。"""
    if not isinstance(person, dict) or not isinstance(templates, dict) or len(templates) > 100:
        raise ValueError('person/templates须为有界对象')
    number = normalize(person['number'], policy)
    if not number['valid']:
        raise ValueError('目标号码格式无效')
    selected = select_devices(devices, [d['key'] for d in devices])
    confirmed = person.get('variant_confirmed', False)
    if type(confirmed) is not bool:
        raise ValueError('variant_confirmed须为布尔值')
    variant = person.get('variant')
    plans = []
    for device in selected:
        kind = label(device['type'])
        config = templates.get(kind)
        if not isinstance(config, dict):
            raise ValueError('设备类型缺少显式模板')
        variants = config.get('variants')
        if not isinstance(variants, dict) or not 1 <= len(variants) <= 20:
            raise ValueError('每类设备须显式提供1至20个variants')
        for name in variants:
            label(name)
        if confirmed:
            if not isinstance(variant, str) or variant not in variants:
                raise ValueError('确认的variant未在设备模板中配置')
            chosen = [variant]
        else:
            chosen = list(variants)
        instructions = []
        for name in chosen:
            spec = variants[name]
            if not isinstance(spec, dict):
                raise ValueError('variant须为对象')
            prefix = spec.get('target_prefix', '')
            if not isinstance(prefix, str) or not re.fullmatch(r'[0-9]{0,6}', prefix):
                raise ValueError('target_prefix须为0至6位数字')
            target = prefix + number['national']
            values = {'target': target, 'device_key': device['key'], 'label': label(device.get('label', device['key']))}
            text = render_template(spec['template'], values, require_target=True)
            instructions.append({'operation': 'target_preview', 'variant': name, 'target': target, 'text': text})
        if 'cancel_template' in config:
            values = {'device_key': device['key'], 'label': label(device.get('label', device['key']))}
            instructions.append({'operation': 'cancel_preview', 'target': None,
                                 'text': render_template(config['cancel_template'], values)})
        plans.append({'key': device['key'], 'type': kind, 'requires_variant_confirmation': not confirmed,
                      'instructions': instructions})
    return {'plan': plans, 'normalization': number, 'state': 'preview_only',
            'template_semantics_verified': False, 'sent': False}


def verify_targets(plan: list[dict[str, Any]], expected: str,
                   allowed_prefixes: list[str]) -> dict[str, Any]:
    """比对目标数字串，不声称已验证任意运营商模板语义或真实生效。"""
    if not isinstance(expected, str) or not re.fullmatch(r'[0-9]{1,32}', expected):
        raise ValueError('expected须为数字文本')
    if not isinstance(allowed_prefixes, list) or not allowed_prefixes or len(allowed_prefixes) > 20:
        raise ValueError('allowed_prefixes须为显式非空数组，可包含空字符串')
    if any(not isinstance(p, str) or not re.fullmatch(r'[0-9]{0,6}', p) for p in allowed_prefixes):
        raise ValueError('允许前缀格式无效')
    if not isinstance(plan, list) or len(plan) > 100:
        raise ValueError('plan须为最多100项数组')
    allowed = {prefix + expected for prefix in allowed_prefixes}
    issues = []
    for item in plan:
        for instruction in item['instructions']:
            if instruction['operation'] != 'target_preview':
                continue
            target, text = instruction.get('target'), instruction.get('text')
            if not isinstance(text, str) or len(text) > 1000:
                raise ValueError('指令text无效')
            numbers = [n for n in re.findall(r'[0-9]+', text) if len(n) >= len(expected)]
            if target not in allowed or target not in numbers or any(n not in allowed for n in numbers):
                issues.append({'key': item['key'], 'variant': instruction.get('variant'), 'reason': 'target_mismatch'})
    return {'ok': not issues, 'issues': issues, 'template_semantics_verified': False, 'sent': False}
