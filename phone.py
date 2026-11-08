"""作者：Wangyuan；日期：2026-10-29；职责：按显式编号格式规范化，不推断归属地。"""
from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class NumberPolicy:
    """全部格式由调用方提供；不含默认国码、区号、运营商或真实号码。"""
    national_lengths: tuple[int, ...]
    national_prefixes: tuple[str, ...] = ()
    country_code: str | None = None
    international_prefix: str | None = None
    trunk_prefix: str | None = None
    allow_bare_country_code: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.national_lengths, (tuple, list)) or not self.national_lengths:
            raise ValueError('national_lengths须为非空数组')
        if any(type(n) is not int or not 1 <= n <= 32 for n in self.national_lengths):
            raise ValueError('编号长度须为1至32的整数')
        if not isinstance(self.national_prefixes, (tuple, list)):
            raise ValueError('national_prefixes须为数组')
        for prefix in self.national_prefixes:
            self._prefix(prefix)
        for prefix in (self.country_code, self.international_prefix, self.trunk_prefix):
            if prefix is not None:
                self._prefix(prefix)
        if type(self.allow_bare_country_code) is not bool:
            raise ValueError('allow_bare_country_code须为布尔值')
        if (self.international_prefix is not None or self.allow_bare_country_code) and self.country_code is None:
            raise ValueError('使用国际前缀或裸国码时须显式提供country_code')
        object.__setattr__(self, 'national_lengths', tuple(self.national_lengths))
        object.__setattr__(self, 'national_prefixes', tuple(self.national_prefixes))

    @staticmethod
    def _prefix(value: Any) -> None:
        if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,6}', value):
            raise ValueError('前缀须为1至6位ASCII数字')

    def matches(self, number: str) -> bool:
        """只做格式匹配，不判断号码存在或属于谁。"""
        return (bool(re.fullmatch(r'[0-9]+', number)) and len(number) in self.national_lengths
                and (not self.national_prefixes or number.startswith(self.national_prefixes)))


def normalize(raw: str | None, policy: NumberPolicy) -> dict[str, Any]:
    """保留去国码/长途前缀线索；不把字母、分机或多个号码拼成有效号码。"""
    if raw is not None and not isinstance(raw, str):
        raise TypeError('号码须为文本或null，避免数值输入丢失前导零')
    if not isinstance(policy, NumberPolicy):
        raise TypeError('须提供NumberPolicy')
    text = (raw or '').strip()
    result = {'raw': text, 'national': None, 'valid': False,
              'country_removed': False, 'trunk_removed': False, 'reason': 'invalid_format'}
    if not text or len(text) > 128 or not re.fullmatch(r'[0-9+ ().-]+', text):
        return result
    if '+' in text[1:] or text.count('+') > 1:
        return result
    depth = 0
    for char in text:
        depth += (char == '(') - (char == ')')
        if depth < 0 or depth > 1:
            return result
    if depth:
        return result
    digits = re.sub(r'[^0-9]', '', text)
    cc, international = policy.country_code, policy.international_prefix
    if text.startswith('+'):
        if cc is None or not digits.startswith(cc):
            result['reason'] = 'country_code_mismatch'
            return result
        digits = digits[len(cc):]
        result['country_removed'] = True
    elif international is not None and digits.startswith(international):
        remainder = digits[len(international):]
        if not remainder.startswith(cc):
            result['reason'] = 'country_code_mismatch'
            return result
        digits = remainder[len(cc):]
        result['country_removed'] = True
    elif policy.allow_bare_country_code and not policy.matches(digits) and digits.startswith(cc):
        digits = digits[len(cc):]
        result['country_removed'] = True
    trunk = policy.trunk_prefix
    if trunk is not None and not policy.matches(digits) and digits.startswith(trunk):
        candidate = digits[len(trunk):]
        if policy.matches(candidate):
            digits = candidate
            result['trunk_removed'] = True
    if policy.matches(digits):
        result.update(national=digits, valid=True, reason=None)
    return result
