# OpenClash 分流配置

本仓库维护一套 OpenClash 的订阅转换模板（`Cash.ini`）与自维护规则集，通过本地 [SubConverter-Extended](https://github.com/Aethersailor/SubConverter-Extended) 生成最终 Clash 配置。

## 目录结构

```
Cash.ini                     # OpenClash 订阅转换模板：规则集 + 策略组 + 节点组
list/                        # 自维护规则源（.list 纯文本格式）
  AI.list                    #   AI 服务合集（OpenAI/Claude/Gemini/Copilot/Meta AI/Perplexity/Grok 等）
  Apple.list                 #   Apple 全家桶合并版（含 Apple Intelligence / iCloud 私密转送）
  Check.list                 #   IP 检测 / 测速站点
  BiliBiliIntl.list          #   B 站港澳台 / 国际版
  HBOAsia.list               #   HBO Asia / HBO GO Asia（上游覆盖不全，自维护）
providers/                   # 预转换的 classical provider yaml（供 Clash 直接下载）
scripts/build_providers.py   # 从 list/ 与上游规则源重新生成 providers/ 的脚本
ini/openclash                # OpenClash 配置备份（订阅地址、密码等敏感信息已用 xxx 打码）
```

## 转换流程

```
机场订阅 → SubConverter-Extended (http://192.168.31.91:25500/sub)
        → 套用本仓库 Cash.ini 模板
        → 生成 Clash 配置（规则集直连本仓库 providers/，不经过转换器中转）
        → OpenClash 应用
```

OpenClash 订阅设置（`config config_subscribe`）：

| 选项 | 值 |
|---|---|
| address | 机场订阅地址（真实值填在路由器上，仓库内为 `xxx`） |
| sub_convert | `1` |
| convert_address | `http://192.168.31.91:25500/sub` |
| template | `https://cdn.jsdelivr.net/gh/setFalcon/clash@main/Cash.ini` |

> 模板地址用 jsdelivr 而不是 raw.githubusercontent.com，因为转换服务对 raw 地址有缓存，改了 Cash.ini 不会及时生效。

## 维护流程

1. 修改 `list/` 下的自维护列表（或调整 `Cash.ini` 的分组/规则集）
2. 重新生成 providers（脚本会自动把 `list/*.list` 同步为 `providers/<name>-classical.yaml`，并转换 `Cash.ini` 中的上游 URL 规则集）：

   ```sh
   python3 -I scripts/build_providers.py
   ```

3. 提交并推送，然后在 OpenClash 中更新订阅即可生效。

新增自维护列表时，文件名（不含 `.list`）需与 `Cash.ini` 里引用的 provider 名一致，例如 `list/HBOAsia.list` → `providers/HBOAsia-classical.yaml`。

## 规则集书写约定（重要）

- **所有 URL 规则集必须预转换为 provider 并使用 `clash-classic:` 前缀**，例如：

  ```
  ruleset=🤖 AI,clash-classic:https://gh-proxy.com/raw.githubusercontent.com/setFalcon/clash/refs/heads/main/providers/AI-classical.yaml,28800
  ```

  原因：裸 `https://...` 规则集会被转换器强制套上它自己的 `127.0.0.1:25500/getruleset` 中转地址，而 Clash 运行在路由器上，本地回环没有这个服务，导致所有规则集下载失败（0 条规则，全部流量落入兜底组）。

- **不要在 ruleset 行写内联规则**（如 `IP-CIDR,x.x.x.x/32`）——转换器会把它当成本地文件路径解析并报错。

- 内置规则（`[]GEOSITE,cn`、`[]GEOIP,cn,no-resolve`）和 `[]FINAL` 可直接使用，无需 provider。

## 上游来源

- 规则列表：<https://github.com/blackmatrix7/ios_rule_script>
- 非标端口直连：<https://github.com/Aethersailor/Custom_OpenClash_Rules>
- 转换服务：[SubConverter-Extended](https://github.com/Aethersailor/SubConverter-Extended)

## 安全约定

- `ini/openclash` 中的订阅地址、dashboard 密码等一律用 `xxx` 占位，真实值只存在于路由器上
- 仓库为公开仓库，任何包含 token / 密码 / 节点链接的文件都不要提交
