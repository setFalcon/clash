#!/usr/bin/env python3
"""
把 Cash.ini 里所有 URL 型 ruleset 预转换为 classical provider yaml，
托管在本仓库 providers/ 目录，并把 Cash.ini 改写为 clash-classic: 直连 URL，
从而摆脱转换器对 127.0.0.1:25500 的依赖。

用法: python3 -I scripts/build_providers.py [--relay http://192.168.31.91:25500]
"""
import base64
import re
import sys
import urllib.request
import urllib.parse
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASH = os.path.join(REPO, 'Cash.ini')
PROVIDERS = os.path.join(REPO, 'providers')
RELAY = 'http://192.168.31.91:25500'
RAW_BASE = 'https://gh-proxy.com/raw.githubusercontent.com/setFalcon/clash/refs/heads/main/providers/'
INTERVAL = '28800'


def b64u(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip('=')


def fetch(url: str) -> str:
    # 优先直连，失败走 31.91 转换器中转
    for candidate in (url, f'{RELAY}/getruleset?type=6&url={b64u(url)}'):
        try:
            req = urllib.request.Request(candidate, headers={'User-Agent': 'curl/8'})
            with urllib.request.urlopen(req, timeout=90) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            last = e
    raise RuntimeError(f'fetch failed: {url} ({last})')


def to_classical(text: str) -> str:
    """把任意规则文本转成 classical payload yaml"""
    rules = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        # 已是 payload yaml 则原样透传
        if s == 'payload:':
            return text
        if s.startswith('- '):
            return text
        t = s.split(',', 1)[0].upper()
        if t in ('DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'IP-CIDR', 'IP-CIDR6', 'IP-ASN',
                 'SRC-IP-CIDR', 'DST-PORT', 'SRC-PORT', 'PROCESS-NAME', 'PROCESS-PATH', 'GEOSITE', 'GEOIP', 'MATCH'):
            rules.append(s)
    if not rules:
        raise RuntimeError('no rules parsed')
    out = ['payload:']
    for r in rules:
        out.append('  - ' + r)
    return '\n'.join(out) + '\n'


def main():
    os.makedirs(PROVIDERS, exist_ok=True)
    lines = open(CASH, encoding='utf-8').read().splitlines()
    new_lines = []
    converted = {}
    for l in lines:
        s = l.strip()
        if not s.startswith('ruleset='):
            new_lines.append(l)
            continue
        body = s[len('ruleset='):]
        group, rest = body.split(',', 1)
        # 内联规则（如 IP-CIDR,192.168.31.91/32）合并进 lan-direct
        if rest.split(',')[0] in ('IP-CIDR', 'IP-CIDR6', 'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD'):
            converted.setdefault('lan-direct', []).append(rest)
            new_lines.append('__INLINE__')
            continue
        # 内置 / FINAL / 已有前缀的原样保留
        if rest.startswith('[]') or rest.startswith('clash-'):
            new_lines.append(l)
            continue
        name = rest.rstrip('/').split('/')[-1].replace('.list', '')
        if name not in converted:
            content = fetch(rest)
            text = to_classical(content)
            fname = f'{name}-classical.yaml'
            with open(os.path.join(PROVIDERS, fname), 'w', encoding='utf-8') as f:
                f.write(text)
            converted[name] = fname
        new_lines.append(f'ruleset={group},clash-classic:{RAW_BASE}{converted[name]},{INTERVAL}')
    # 处理内联规则
    if 'lan-direct' in converted:
        rules = converted['lan-direct']
        text = 'payload:\n' + ''.join(f'  - {r}\n' for r in rules)
        with open(os.path.join(PROVIDERS, 'lan-direct-classical.yaml'), 'w', encoding='utf-8') as f:
            f.write(text)
    final = []
    for l in new_lines:
        if l == '__INLINE__':
            continue
        final.append(l)
    # 把内联行替换成一条 lan-direct provider 行（插到 GEOSITE 前）
    out = []
    inserted = False
    for l in final:
        if not inserted and l.startswith('ruleset=') and '[]GEOSITE' in l:
            out.append(f'ruleset=🎯 全球直连,clash-classic:{RAW_BASE}lan-direct-classical.yaml,{INTERVAL}')
            inserted = True
        out.append(l)
    open(CASH, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print(f'生成 {len(converted)} 个 provider 文件到 {PROVIDERS}')


if __name__ == '__main__':
    main()
