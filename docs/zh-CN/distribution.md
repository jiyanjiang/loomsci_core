# 分发模型 · Core + Apps

- 状态：草案，2026-11-14
- 关联：`core-contract.md`、`app-manifest.md`

## 1. 仓库

```text
loomsci_core      公开   Core 运行时、CLI、App Host、SDK
loomsci_report    公开   Report App + 安装器
loomsci_project   后续   Project App
```

规则：

- Core 与 App 独立版本
- App 依赖 `core/1`，不复制 Core 内部实现
- Core 发布慢；App 可以快
- 用契约测试保证兼容，不共享源文件
- Core 仓库拥有 manifest schema 和示例 App

## 2. 入口

大多数用户从 Report 进入：

```text
LoomSci Report installer
→ 检测/安装 Core
→ 安装 Report
→ 启动 Core + Report
```

高级用户可以只装 Core：

```text
loomsci-core installer
→ 仅 Core
→ 以后安装 App
```

两种入口都不要求注册。

## 3. 包校验

每个下载产物包含：

```text
name version platform arch sha256 signature min_core max_core published_at
```

安装器必须在解压前校验。校验失败不得留下半安装状态。

## 4. 离线与弱网

- Core 完全离线可用
- Report 本地阅读离线可用
- 免费内容包可缓存
- 付费/云功能可要求联网，但必须优雅失败
- Core 启动不得被网络调用阻塞

## 5. 更新分离

```text
Core 软件更新    → Core updater
App 软件更新     → App Host
内容更新         → App/content channel
权益更新         → App/account layer
```

内容更新不得安装可执行代码。App 更新不得重写 Core。

## 6. 付费 App 与内容

- Core 免费、本地
- Report/Project 可以有免费本地功能和付费云/内容功能
- entitlement 由 App 拥有并签名
- Core 不做计费、积分、用户身份
- 不注册也保留完整本地 Core + App 功能
- 付费内容可以要求账号，但不能禁用本地数据访问

## 7. 发布门禁

1. 干净机器安装
2. Core 离线启动
3. App 安装/启动/停止/更新/卸载
4. App 更新后备份/恢复
5. 内容包应用/回滚
6. 签名失败测试
7. Report bootstrap 不创建重复工作区
8. 卸载保留数据
