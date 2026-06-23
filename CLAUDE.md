# CLAUDE.md — 全能办公工具箱 (OmniOffice Toolkit)

> **在编写任何代码之前，必须先阅读本文件。** 本文件定义了项目的架构规范、编码约定和开发流程。所有代码变更必须严格遵守本文档。

---

## 一、项目概述

**全能办公工具箱** 是一款 Windows 平台的本地离线办公工具集合，基于 Python + PySide6 构建。

- **目标用户**：需要本地离线处理办公文件的 Windows 用户
- **核心原则**：无广告、不联网、保护隐私、本地处理
- **语言**：默认为中文（zh_CN），支持国际化
- **Python 环境**：使用 Anaconda Python（`D:\ruanjian\ANACONDA\python.exe`），以确保 PySide6 DLL 兼容性

## 二、技术栈

| 层 | 技术 | 用途 |
|---|---|---|
| UI 框架 | PySide6 ≥ 6.9.0 | Qt6 Python 绑定，主界面 |
| 图像处理 | Pillow, OpenCV, scikit-image, rembg | 图片压缩、编辑、去背景等 |
| PDF | pdfplumber, pikepdf, PyPDF2 | PDF 解析、合并、拆分 |
| Office | python-docx, openpyxl, python-pptx | Word/Excel/PPT 读写 |
| 二维码 | qrcode, pyzbar | 二维码生成与识别 |
| 日志 | loguru | 结构化日志 |
| 配置 | pyyaml | YAML 配置文件读写 |
| 编码检测 | chardet | 文本文件编码检测 |
| 线程池 | Qt QThreadPool | 异步任务执行 |

## 三、项目目录结构

```
全能办公工具箱/
├── main.py                 # 入口文件，启动 QApplication
├── run.bat                 # Windows 启动脚本（Anaconda Python）
├── requirements.txt        # pip 依赖清单
├── CLAUDE.md               # 本文件 — 项目开发规范
├── .gitignore
│
├── src/
│   ├── __init__.py
│   ├── app.py              # App 类（QApplication 子类），管理应用生命周期
│   ├── constants.py         # 全局常量（路径、模块ID、文件格式等）
│   │
│   ├── core/               # 核心基础设施（单例模式为主）
│   │   ├── config_manager.py   # 配置管理器（YAML，线程安全单例）
│   │   ├── event_bus.py        # 事件总线（发布/订阅，解耦模块通信）
│   │   ├── i18n_manager.py     # 国际化管理（JSON 翻译文件）
│   │   ├── theme_manager.py    # 主题管理（暗黑/亮色 + QSS）
│   │   ├── log_manager.py      # 日志管理（loguru 配置）
│   │   ├── path_manager.py     # 输出路径管理（防冲突）
│   │   ├── plugin_manager.py   # 模块发现与注册
│   │   ├── task_queue.py       # 多线程任务队列（单例 QObject）
│   │   └── task_worker.py      # 任务工作器基类（QRunnable）
│   │
│   ├── modules/            # 功能模块（插件式，自动发现）
│   │   ├── base_module.py      # 模块抽象基类
│   │   ├── image_processing/   # 图片处理（压缩/水印/编辑/OCR/二维码/去背景/证件照）
│   │   ├── pdf_tools/          # PDF 工具（合并/拆分/提取/转换）
│   │   ├── office_tools/       # Office 文档工具
│   │   ├── batch_tools/        # 批量文件处理
│   │   ├── efficiency_tools/   # 效率工具（便签/剪贴板等）
│   │   ├── ai_tools/           # AI 智能工具（文本/图像/助手）
│   │   └── mind_map/           # 思维导图
│   │
│   ├── ui/                 # UI 层
│   │   ├── main_window.py      # 主窗口（左侧导航 + 右侧工作区）
│   │   ├── components/         # 可复用 UI 组件（设置对话框、拖拽区、文件列表等）
│   │   ├── widgets/            # 自定义控件
│   │   ├── styles/             # QSS 样式文件（dark.qss, light.qss）
│   │   └── resources/         # UI 资源（图标等）
│   │
│   └── services/           # 共享业务服务
│       ├── file_service.py
│       └── export_service.py
│
├── resources/              # 静态资源
│   └── i18n/               # 翻译文件（zh_CN.json 等）
│
├── data/                   # 运行时数据（自动创建，不提交 Git）
│   ├── config.yaml
│   ├── logs/
│   └── models/
│
└── tests/                  # 测试
    └── __init__.py
```

## 四、核心架构设计

### 4.1 应用生命周期

```
main.py → App.__init__() → _init_dirs() → _init_logging() → _init_config()
         → _init_i18n() → _init_theme() → _init_path_manager()
         → App.run() → QTimer.singleShot(0, _create_main_window)
         → MainWindow._load_modules() → PluginManager.discover_modules()
```

- `App` 是 `QApplication` 的子类，负责顺序初始化所有核心服务
- 主窗口通过 `QTimer.singleShot(0, ...)` 延迟创建，确保 Qt 完全初始化

### 4.2 模块系统（插件架构）

每个功能模块必须：

1. 在 `src/modules/<module_name>/` 下创建目录
2. 目录中必须包含 `module.py`，其中定义一个继承 `BaseModule` 的类
3. 由 `PluginManager` 自动扫描发现（无需手动注册）

**模块基类要求：**
```python
class SomeModule(BaseModule):
    module_id: str = "unique_id"      # 唯一标识符，对应 constants.py 中的 MODULE_* 常量
    module_name: str = "显示名称"       # 导航栏显示名称
    module_icon: str = "nav_xxx"      # 图标键名（对应 ICONS_DIR 下的 svg 文件）
    module_order: int = 100           # 导航栏排序（数值越小越靠前）
    category: str = "core"            # core | productivity | ai

    def create_main_view(self) -> QWidget:
        """必须实现：返回模块的主视图 QWidget"""
        ...
```

**模块发现机制**：`PluginManager` 遍历 `src/modules/` 下的每个子目录，查找 `module.py` 中的 `BaseModule` 子类并实例化。

### 4.3 任务系统

所有文件处理操作必须通过 `TaskQueue` + `TaskWorker` 执行：

```
用户操作 → TaskItem 创建 → TaskQueue.submit(task)
         → QThreadPool 执行 TaskWorker.process()
         → signals 通知进度/完成/失败
```

**关键规则：**
- `TaskWorker` 继承 `QRunnable`，在 `process()` 中实现处理逻辑
- 长时间循环中调用 `check_pause()` 支持暂停
- 通过 `self.report_progress(percent, message)` 报告进度
- Worker 通过 `TaskQueue.register_worker(task_type, WorkerClass)` 注册
- **绝对不能**在主线程（GUI 线程）中执行耗时操作

### 4.4 事件总线

模块间通信使用 `EventBus`（发布/订阅模式），**禁止模块间直接导入**：

```python
from src.core.event_bus import EventBus, Events

# 发布
EventBus().publish(Events.TASK_COMPLETED, task_id="xxx")

# 订阅
EventBus().subscribe(Events.THEME_CHANGED, self._on_theme_changed)
```

常用事件类型定义在 `Events` 类中（`src/core/event_bus.py`）。

### 4.5 配置管理

- `ConfigManager` 是线程安全单例，使用 YAML 持久化
- 通过点号分隔的键路径访问：`config.get("app.theme")`
- 默认配置定义在 `config_manager.py` 的 `DEFAULT_CONFIG` 字典中
- 新增配置项时，必须同时在 `DEFAULT_CONFIG` 中添加默认值

### 4.6 国际化 (i18n)

- 翻译文件为 `resources/i18n/<lang_code>.json`，使用点号分隔的键
- 使用 `tr("key.path", **kwargs)` 进行翻译，支持变量替换
- 新 UI 文本必须使用 `tr()` 包裹，同时在 `zh_CN.json` 中添加对应条目
- 当前支持：`zh_CN`

### 4.7 主题系统

- 由 `ThemeManager` 管理（`src/core/theme_manager.py`）
- 支持暗黑（dark）和亮色（light）主题
- QSS 样式文件位于 `src/ui/styles/`
- 主题色和字体大小可通过配置切换

## 五、编码规范

### 5.1 Python 代码风格

- **Python 版本**：3.13+
- **类型注解**：所有公共方法必须包含完整的类型注解
- **文档字符串**：使用 Google 风格的 docstring（`Args:`, `Returns:`, `Raises:`）
- **命名约定**：
  - 类名：`PascalCase`
  - 方法和函数：`snake_case`
  - 私有成员：前缀 `_`（如 `_internal_method`）
  - 常量：`UPPER_SNAKE_CASE`
  - 模块 ID：`snake_case`（如 `image_processing`）
- **导入顺序**：标准库 → 第三方库 → 本地模块，每组之间空一行

### 5.2 PySide6 规范

- **UI 与逻辑分离**：视图（View）负责 UI 布局，引擎（Engine/Worker）负责业务逻辑
- **信号槽命名**：信号名使用 `snake_case`，槽函数前缀 `_on_`
- **耗时操作**：绝不在主线程执行，使用 `TaskQueue` + `TaskWorker`
- **QSS 选择器**：使用 `setObjectName()` 设置对象名，在 QSS 中使用 `#objectName` 选择器
- **布局**：使用代码布局（不使用 Qt Designer/.ui 文件），保证完全可控

### 5.3 文件组织

- 每个功能模块的目录结构：
  ```
  src/modules/<module_name>/
  ├── __init__.py
  ├── module.py            # BaseModule 子类，模块入口
  ├── <feature>_engine.py  # 业务逻辑引擎（可选，复杂逻辑）
  ├── <feature>_worker.py  # TaskWorker 子类（可选，异步任务）
  └── views/
      ├── __init__.py
      └── <feature>_view.py  # UI 视图
  ```
- Worker 的注册放在 `module.py` 中，随模块加载自动完成

### 5.4 错误处理

- 使用 `loguru` 记录日志，不使用 `print()`
- Worker 的 `process()` 方法中抛出异常会被 TaskQueue 自动捕获并标记为失败
- UI 层的异常不应静默吞掉，至少记录到日志
- 文件操作前检查路径有效性

### 5.5 Git 规范

- **禁止提交**：`data/`、`__pycache__/`、`venv/`、`*.pyc`、构建产物
- **提交信息**：使用中文描述，格式为 `<模块>: <简述>`
- **分支策略**：`master` 为主分支，功能开发在特性分支进行

## 六、开发流程

### 6.1 添加新功能模块

1. 创建目录 `src/modules/<new_module>/` 及 `__init__.py`
2. 创建 `module.py`，定义继承 `BaseModule` 的模块类
3. 在 `src/constants.py` 中添加 `MODULE_<NAME> = "<new_module>"`
4. 实现 `create_main_view()` 返回模块主视图
5. 如需异步处理：创建 Worker 类继承 `TaskWorker`，实现 `process()`
6. 在 `module.py` 中调用 `TaskQueue.register_worker()` 注册 Worker
7. 在 `resources/i18n/zh_CN.json` 中添加翻译条目
8. 创建视图文件放在 `views/` 目录下

### 6.2 添加新的翻译条目

1. 在代码中使用 `tr("some.key")`
2. 在 `zh_CN.json` 中添加 `"some.key": "中文翻译"`
3. 键名使用小写 + 点号分隔，按功能分组

### 6.3 修改配置项

1. 在 `DEFAULT_CONFIG` 字典中添加默认值
2. 通过 `config.get()` / `config.set()` 读写
3. 如需 UI 设置入口，在 `SettingsDialog` 中添加对应控件

### 6.4 运行与调试

```batch
# 使用项目自带的启动脚本
run.bat

# 或直接用 Anaconda Python 运行
D:\ruanjian\ANACONDA\python.exe main.py
```

## 七、重要约束

1. **本地离线优先**：所有功能默认在本地完成，除非用户明确要求网络功能
2. **线程安全**：访问共享状态（ConfigManager, TaskQueue）时注意线程安全
3. **单例模式**：ConfigManager、EventBus、I18nManager、TaskQueue、PluginManager 均为单例，不要尝试创建新实例
4. **模块隔离**：模块之间不能直接导入对方的视图或引擎，通过 EventBus 通信
5. **输出安全**：处理文件时绝不要覆盖原始文件，使用 `PathManager` 生成输出路径
6. **Anaconda Python**：本项目依赖 Anaconda Python 的 DLL 环境，不要切换到其他 Python 发行版
7. **编码格式**：所有源文件使用 UTF-8 编码
8. **不要提交 `data/` 目录**：其中包含运行时生成的配置文件、日志和模型

## 八、当前状态

- **版本**：0.1.0（早期开发阶段）
- **已完成**：核心框架（配置、日志、国际化、主题、事件总线、模块系统、任务队列）、主窗口 UI、图片处理模块（含 7 个子功能）
- **进行中**：PDF 工具、Office 文档工具
- **待开发**：批量文件处理、效率工具、AI 工具、思维导图
- **已注册 Worker**：`compress_image`, `add_watermark`, `edit_image`, `ocr_image`, `qrcode`, `remove_background`, `id_photo`
