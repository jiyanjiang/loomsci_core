# 签名与信任契约 · v0

- 状态：M0 草案，2026-11-14
- 范围：Core 包、官方 App 包、内容包
- 算法：Ed25519
- 平台：macOS 与 Windows 为一等测试目标

## 1. 目标

- 篡改包在解压前被拒绝
- 合法包可离线验证
- 密钥可轮换且不破坏现有安装
- 密钥泄露可撤销
- 验证失败不留半安装状态
- 用户不需要账号或网络即可验证本地包

## 2. 信任层级

```text
Root key（离线）
├─ Release key   → Core 包、官方 App 包
└─ Content key   → 内容包（不能是代码）
```

v0：

- 一把 root、一把 release、一把 content
- 官方 App 由 release key 签名
- 第三方 App 签名机制后置
- root 私钥离线，release/content 私钥在 CI

## 3. 公钥分发

安装器与 Core 携带：

```text
trust/root.pub
trust/release.cert
trust/content.cert
trust/revocations.json
```

- `root.pub` 是信任锚；fingerprint 写入发布说明
- `release.cert` / `content.cert` 包含公钥、key id、角色、有效期，由 root 签名
- 安装器在源码中 pin root fingerprint，用 release cert 验证 Core
- Core 用同一 trust 目录验证 App 与内容包
- 安装过程中不从网络取公钥

## 4. 包格式

```text
package/
├─ manifest.json
├─ manifest.sig
└─ payload/
```

`manifest.json` 至少包含：

```json
{
  "kind": "core | app | content",
  "name": "...",
  "version": "...",
  "platform": "macos-arm64 | windows-x64 | any",
  "created_at": "...",
  "payload_sha256": "...",
  "payload_bytes": 0,
  "key_id": "..."
}
```

签名：

- Ed25519 签 canonical JSON：
  `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`
- detached `manifest.sig`，base64
- 签名覆盖 manifest；`payload_sha256` 绑定 payload
- 校验签名、key role、有效期、key id、payload hash、payload size

## 5. 验证顺序

```text
1. 读 manifest + signature
2. 按 key_id 在 trust/ 找 key
3. 验证 cert 链到 pinned root
4. 检查 key role（release/content）
5. 检查有效期/撤销
6. 验证 manifest 签名
7. 验证 payload_sha256 / payload_bytes
8. 解压到临时目录
9. 验证解压树 hash
10. 原子安装
```

任一失败：

- 解压前停止或切换前停止
- 清理临时文件
- 保留现有安装
- 返回具体错误码

## 6. 错误码

```text
signature_missing
signature_invalid
key_unknown
key_revoked
key_expired
key_role_mismatch
manifest_invalid
payload_hash_mismatch
payload_size_mismatch
payload_extract_failed
```

不能只报 “install failed”。

## 7. 密钥轮换

- release/content 由 root 签发新 cert
- 旧 cert 至少重叠两个版本
- root 轮换：
  1. 新 root 签发包含两个 fingerprint 的 transition cert
  2. 仍 pin 旧 root 的安装器在重叠期接受新 root
  3. 下一个 Core 版本 pin 新 root
  4. 重叠结束后退役旧 root
- 每次轮换写入 release notes

## 8. 撤销

`trust/revocations.json` 由 root 签名：

```json
{
  "issued_at": "...",
  "keys": [{"key_id": "...", "reason": "compromised", "effective_at": "..."}]
}
```

- Core 使用前检查撤销
- 离线安装使用随包撤销列表
- 在线更新可刷新，但无网络不得阻塞本地使用
- 被撤销 key 不能签新包；已安装包不删除，但后续更新拒绝

## 9. 平台注意

### 通用

- Ed25519 验证与 OS 无关
- 文件写入使用原子替换
- 私钥不写入工作区、日志或包

### macOS

- v0 使用 checksum + Ed25519；Apple 公证是后续分发任务
- 安装器不得依赖 Gatekeeper bypass
- `~/.loomsci` 属于用户；无需管理员权限

### Windows

- v0 使用 checksum + Ed25519；Authenticode 是后续任务
- 安装在用户目录，无需管理员权限
- 文件锁要求先停止再替换

## 10. 测试矩阵

所有签名测试必须在 **macOS 与 Windows** 通过，M0 才能关闭。

| ID | 测试 | 期望 |
|---|---|---|
| S1 | 合法 Core 包 | 安装成功 |
| S2 | 篡改 manifest | `signature_invalid` |
| S3 | 篡改 payload | `payload_hash_mismatch` |
| S4 | 缺签名 | `signature_missing` |
| S5 | 错误 key id | `key_unknown` |
| S6 | 被撤销 key | `key_revoked` |
| S7 | 过期 cert | `key_expired` |
| S8 | content key 签可执行 App | `key_role_mismatch` |
| S9 | 离线验证 | 无网络成功 |
| S10 | 验证失败不留半安装 | 目录不变 |
| S11 | 轮换重叠期 | 旧/新 key 均可验证 |
| S12 | 文件截断 | 解压前拒绝 |

## 11. 验收

1. S1–S12 在 macOS 通过
2. S1–S12 在 Windows 通过
3. 私钥不出现在仓库、日志、包中
4. 验证失败后现有安装字节不变
5. 安装器返回具体错误码
6. 同一签名包在两个平台均可验证
7. 内容包不能用于安装代码
8. root fingerprint 写入发布说明

## 12. 待定

- v0 使用单一 release key 还是 per-app key
- 撤销刷新周期与离线宽限
- Authenticode/公证的时间点
- 第三方 App 签名策略
