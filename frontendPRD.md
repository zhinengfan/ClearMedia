
## **ClearMedia 前端应用需求文档 (v1.0)**

### **1. 项目概述**

#### **1.1 项目目标**
开发一个现代、轻量且高效的Web管理界面，作为 ClearMedia 后端服务的用户交互前端。该界面需为熟悉技术的NAS用户提供对媒体库整理状态的全面监控、诊断和管理能力。

#### **1.2 目标用户**
拥有NAS设备、熟悉Docker环境、并期望对个人媒体库进行自动化整理的家庭用户。

### **2. 技术栈与环境**

| 类别             | 技术/工具             | 版本/要求                               |
| :--------------- | :-------------------- | :-------------------------------------- |
| **包管理器**     | **pnpm**              | 最新                                  |
| **构建工具**     | **Vite**              | 最新稳定版                              |
| **前端框架**     | **React**             | v19+            |
| **UI组件库**     | **shadcn/ui**         | 最新                |
| **样式方案**     | **Tailwind CSS**      | v4，配置需遵循项目提供的设计令牌     |
| **语言**         | **TypeScript**        | 严格模式                                |

### **3. 功能需求 (Functional Requirements)**

#### **3.1 整体布局与导航**
*   **FR-1.1 (主布局):** 应用需采用固定的“左侧边栏导航 + 右侧主内容区”的经典仪表盘布局。
*   **FR-1.2 (侧边栏导航):**
    *   侧边栏需包含以下可点击的导航链接，并附带对应的`lucide-react`图标：
        *   **仪表盘 (Dashboard)**
        *   **文件管理 (Files)**
        *   **设置 (Settings)**
    *   当前激活的导航链接必须有视觉上的高亮状态。
*   **FR-1.3 (响应式):** 布局需具备基本的响应式能力，确保在桌面和主流平板设备上均有良好的可读性和可操作性。

#### **3.2 仪表盘 (Dashboard)**
*   **FR-2.1 (统计卡片):**
    *   页面顶部需展示至少4个核心统计卡片 (`Card`)，分别显示：**已完成**、**处理中**、**待处理**、**总计**的文件数量。
    *   数据需通过调用后端 `GET /api/stats` 接口获取。
    *   “待处理”卡片必须是可点击的，点击后导航至“文件管理”页并自动筛选出所有待处理状态的文件。
*   **FR-2.2 (状态分布图):** 需使用图表组件（如 `recharts` 的环形图）将各状态文件数量占比进行可视化展示。
*   **FR-2.3 (近期活动):** 需展示一个简洁的表格，列出最近处理的5个文件及其状态和处理时间。数据通过调用 `GET /api/files` 获取。

#### **3.3 文件管理 (Files)**
*   **FR-3.1 (文件列表):**
    *   需使用可复用的数据表格 (`DataTable`) 组件展示文件列表。
    *   表格必须包含以下列：`原始文件名`, `状态`, `识别标题`, `类型`, `年份`, `更新时间`。
    *   `状态`列必须使用不同颜色的徽章 (`Badge`) 组件进行视觉区分（如绿-成功, 红-失败, 黄-警告, 蓝-处理中）。
    *   表格必须支持分页，并能正确调用后端分页接口。
*   **FR-3.2 (筛选与搜索):**
    *   页面顶部必须提供一个搜索框 (`Input`)，用于按文件名模糊搜索。搜索操作需进行防抖处理。
    *   必须提供一个状态筛选器 (`DropdownMenu`)，允许用户选择一个或多个状态进行组合筛选。
    *   所有筛选、搜索、分页的状态都必须实时同步到URL的查询参数中，以支持刷新和深度链接。
*   **FR-3.3 (文件详情面板):**
    *   点击表格中的任意一行，必须从页面右侧滑出一个详情面板 (`Sheet`)，主列表背景变暗。
    *   详情面板的显示状态必须由URL查询参数（如 `?details={file_id}`）控制。
    *   面板内必须清晰展示该文件的详细信息，包括：
        1.  TMDB返回的媒体海报图片。
        2.  LLM分析的原始JSON结果。
        3.  生成的最终目标路径，并提供一键复制功能。
        4.  当文件状态为`FAILED`或`CONFLICT`时，必须在醒目位置展示具体的错误信息。
*   **FR-3.4 (重试操作):**
    *   在详情面板中，当文件状态为 `FAILED`, `NO_MATCH`, 或 `CONFLICT` 时，必须提供一个可点击的“重试处理”按钮。
    *   点击该按钮后，需调用后端 `POST /api/files/{file_id}/retry` 接口，并向用户提供操作反馈（如按钮加载状态）。
    *   重试成功后，文件列表的数据应自动刷新以展示最新状态。

#### **3.4 设置 (Settings)**
*   **FR-4.1 (配置加载与展示):** 页面加载时，需调用 `GET /api/config` 接口获取当前配置，并填充到表单中。
*   **FR-4.2 (配置修改):**
    *   需提供一个表单，允许用户修改后端API白名单中的配置项（如 `LOG_LEVEL`, `TMDB_CONCURRENCY` 等）。
    *   表单输入项应使用合适的组件（如 `Select` 用于选择，`Input type="number"` 用于数字）。
*   **FR-4.3 (保存与反馈):**
    *   提供一个“保存更改”按钮，该按钮在表单内容未被修改时应处于禁用状态。
    *   点击保存时，需调用 `POST /api/config` 接口，只提交被修改过的字段。
    *   操作过程中需提供明确的视觉反馈（按钮加载状态），并在操作完成后通过 `Toast` 通知用户成功或失败。


### design tokens
```json
{
  "colors": {
    "brand": {
      "primary": "#22C55E",
      "primaryHover": "#16A34A"
    },
    "background": {
      "default": "#FFFFFF",
      "subtle": "#F8FAFC",
      "sidebar": "#F8FAFC"
    },
    "text": {
      "default": "#0F172A",
      "muted": "#64748B",
      "subtle": "#94A3B8",
      "onBrand": "#FFFFFF"
    },
    "border": {
      "default": "#E2E8F0",
      "subtle": "#F1F5F9"
    },
    "semantic": {
      "success": {
        "foreground": "#15803D",
        "background": "#F0FDF4"
      },
      "info": {
        "foreground": "#2563EB",
        "background": "#EFF6FF"
      },
      "warning": {
        "foreground": "#D97706",
        "background": "#FEFCE8"
      },
      "danger": {
        "foreground": "#DC2626",
        "background": "#FEF2F2"
      }
    },
    "chart": {
      "blue": "#3B82F6",
      "orange": "#F97316",
      "cyan": "#22D3EE",
      "pink": "#EC4899",
      "purple": "#8B5CF6",
      "green": "#22C55E",
      "yellow": "#EAB308",
      "red": "#EF4444"
    }
  },
  "typography": {
    "fontFamily": {
      "sans": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif"
    },
    "fontSize": {
      "xs": "0.75rem",
      "sm": "0.875rem",
      "base": "1rem",
      "lg": "1.125rem",
      "xl": "1.25rem",
      "2xl": "1.5rem",
      "3xl": "1.875rem"
    },
    "fontWeight": {
      "normal": "400",
      "medium": "500",
      "semibold": "600",
      "bold": "700"
    },
    "lineHeight": {
      "none": "1",
      "tight": "1.25",
      "normal": "1.5",
      "loose": "2"
    }
  },
  "spacing": {
    "0": "0px",
    "1": "4px",
    "2": "8px",
    "3": "12px",
    "4": "16px",
    "5": "20px",
    "6": "24px",
    "8": "32px",
    "10": "40px",
    "12": "48px"
  },

  "borderRadius": {
    "none": "0px",
    "sm": "0.25rem",
    "md": "0.5rem",
    "lg": "0.75rem",
    "full": "9999px"
  },
  "boxShadow": {
    "sm": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
    "default": "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    "md": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)"
  },
  "zIndex": {
    "dropdown": 10,
    "sheet": 20,
    "modal": 30,
    "tooltip": 40
  },
  "transitions": {
    "duration": "200ms",
    "easing": "cubic-bezier(0.4, 0, 0.2, 1)"
  }
}
```