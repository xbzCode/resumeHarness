"""P1 阶段测试数据初始化脚本。

用法:
    cd ResumeHarness
    python scripts/seed_test_data.py

功能:
    1. 创建用户目录结构
    2. 写入示例简历原文
    3. 写入记忆文件（职业偏好/技能标签/优化历史）
    4. 保存示例简历快照
    5. 保存用户配置
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# 确保项目根目录在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent))

from resume_agent.config.settings import get_settings, UserSettings, save_user_settings
from resume_agent.memory.paths import ensure_user_dirs
from resume_agent.memory.manager import write_memory_file
from resume_agent.resume_renderer import save_resume_snapshot

# ============================================================================
# 示例简历原文
# ============================================================================

SAMPLE_RESUME_MD = """\
# 张三

## 个人简介

5 年前端开发经验，精通 React/Vue 技术栈，有大型 SPA 项目架构经验，关注性能优化和用户体验。

## 工作经历

### ABC 科技有限公司 | 高级前端工程师 | 2021.03 - 至今
- 负责公司核心产品的前端架构设计和开发
- 主导前端工程化改造，将构建速度提升 60%
- 带领 5 人前端团队完成 3 个大型项目交付

### XYZ 互联网公司 | 前端工程师 | 2018.07 - 2021.02
- 参与电商平台 H5 开发，日活用户 50 万+
- 开发组件库，提升团队开发效率 30%
- 负责移动端性能优化，首屏加载时间从 3s 降至 1.2s

## 教育背景

### 某某大学 | 计算机科学与技术 | 本科 | 2014.09 - 2018.06

## 技能标签

- 前端框架：React、Vue 3、Next.js
- 语言：TypeScript、JavaScript、HTML5、CSS3
- 工具链：Webpack、Vite、Git、Docker
- 其他：Node.js、GraphQL、CI/CD

## 项目经历

### 电商平台前端重构 | 核心开发者 | 2022.01 - 2022.06
- **项目描述**：对日活 50 万+ 的电商平台进行前端架构升级
- **核心贡献**：设计微前端架构方案，实现多团队并行开发；优化首屏加载性能，FCP 从 3.2s 降至 0.8s
"""

# ============================================================================
# 示例 JD（职位描述）
# ============================================================================

SAMPLE_JD = """
## 字节跳动 - 高级前端工程师

### 岗位职责
1. 负责抖音电商前端架构设计和核心功能开发
2. 主导前端性能优化，保障大规模用户下的流畅体验
3. 推动前端工程化和基础设施建设，提升团队研发效率
4. 参与技术方案评审，推动技术选型和最佳实践

### 任职要求
1. 本科及以上学历，计算机相关专业优先
2. 5 年以上前端开发经验，3 年以上大型项目经验
3. 精通 React/Vue 至少一种框架，了解其底层原理
4. 熟练使用 TypeScript，有复杂类型系统设计经验
5. 有前端性能优化实战经验，熟悉 Core Web Vitals
6. 有微前端/模块联邦架构经验优先
7. 有 Node.js/BFF 开发经验优先
8. 良好的沟通能力和团队协作精神
"""

# ============================================================================
# 示例简历快照（LLM 优化后的输出格式）
# ============================================================================

SAMPLE_OPTIMIZED_RESUME = """\
# 张三

## 个人简介

5 年前端开发经验，精通 React/Vue 技术栈与微前端架构，主导过日活 50 万+ 电商平台前端重构，首屏性能优化 FCP 从 3.2s 降至 0.8s。擅长前端工程化建设与团队技术赋能。

## 工作经历

### ABC 科技有限公司 | 高级前端工程师 | 2021.03 - 至今
- **架构升级**：主导前端工程化改造，引入 Vite + TypeScript 技术栈，构建速度提升 60%，CI/CD 流水线部署效率提升 40%
- **团队管理**：带领 5 人前端团队，建立 Code Review 规范和技术分享机制，团队交付效率提升 35%
- **性能优化**：实施代码分割与懒加载策略，核心页面 LCP 从 2.8s 优化至 1.1s，Core Web Vitals 全部达标

### XYZ 互联网公司 | 前端工程师 | 2018.07 - 2021.02
- **电商平台**：参与日活 50 万+ H5 电商开发，实现商品详情页秒开，用户转化率提升 12%
- **组件库建设**：开发并维护 40+ 通用组件库，覆盖率达 85%，团队开发效率提升 30%
- **性能攻坚**：采用 SSR + 骨架屏方案，首屏加载时间从 3s 降至 1.2s，跳出率降低 18%

## 教育背景

### 某某大学 | 计算机科学与技术 | 本科 | 2014.09 - 2018.06

## 技能标签

- **前端框架**：React（精通，了解 Fiber 架构）、Vue 3（精通，Composition API）、Next.js
- **语言**：TypeScript（复杂类型系统设计）、JavaScript（ES6+）、HTML5/CSS3
- **工程化**：Webpack/Vite（插件开发）、Monorepo（Turborepo）、Docker、CI/CD
- **架构**：微前端（qiankun/Module Federation）、SSR、BFF（Node.js）
- **其他**：GraphQL、性能监控（Sentry）、自动化测试（Jest/Cypress）

## 项目经历

### 电商平台前端重构 | 核心开发者 | 2022.01 - 2022.06
- **项目描述**：对日活 50 万+ 电商平台进行前端架构升级，从 jQuery 迁移至 React + 微前端架构
- **核心贡献**：
  - 设计基于 qiankun 的微前端架构方案，实现 4 个业务团队并行开发，发版效率提升 50%
  - 实施 SSR + 流式渲染方案，FCP 从 3.2s 降至 0.8s，SEO 流量提升 25%
  - 搭建前端监控体系，接入 Sentry + 自研性能采集，线上问题平均发现时间从 2h 缩短至 15min
"""

# ============================================================================
# 记忆文件内容
# ============================================================================

CAREER_PREFERENCE = """\
## 求职偏好

- 目标岗位：高级前端工程师 / 前端架构师
- 目标公司：互联网大厂（字节、阿里、腾讯）
- 期望薪资：面议
- 工作地点：北京 / 远程

## 写作风格偏好

- 简历使用 STAR 法则描述工作成果
- 优先量化成果（如：提升 XX%、降低 XX%）
- 技能标签按熟练度分级标注
- 不使用过于口语化的表达
"""

SKILL_TAGS = """\
## 核心技能

### 前端框架
- React: 5年，精通（Fiber、Hooks、Concurrent Mode）
- Vue 3: 3年，精通（Composition API、响应式原理）
- Next.js: 2年，熟练

### 语言
- TypeScript: 4年，精通（泛型、类型体操）
- JavaScript: 5年，精通（ES6+、异步编程）

### 工程化
- Webpack/Vite: 4年，精通（插件开发、构建优化）
- Docker/CI/CD: 2年，熟练
- Monorepo: 1年，了解

### 架构
- 微前端: 2年，熟练（qiankun/Module Federation）
- SSR: 1年，了解
- Node.js/BFF: 2年，熟练
"""

OPTIMIZATION_HISTORY = """\
## 2024-04-15 第 1 次优化

- 针对字节跳动高级前端工程师岗位优化
- 调整策略：突出微前端和性能优化经验
- 量化成果：将模糊描述改为具体数字
- 技能分级：按熟练度标注技能等级
- 输出模板：professional（简洁商务风）
"""


def seed() -> None:
    """写入测试数据。"""
    settings = get_settings()
    user_id = settings.effective_default_user_id

    print(f"=== P1 测试数据初始化 (user_id={user_id}) ===\n")

    # 1. 创建目录
    user_dir = ensure_user_dirs(user_id)
    print(f"[1/5] 用户目录已创建: {user_dir}")

    # 2. 写入简历原文
    memory_dir = settings.get_user_memory_dir(user_id)
    resume_path = memory_dir / "简历原文.md"
    resume_path.write_text(SAMPLE_RESUME_MD, encoding="utf-8")
    print(f"[2/5] 简历原文已写入: {resume_path}")

    # 3. 写入记忆文件
    write_memory_file(user_id, "职业偏好.md", CAREER_PREFERENCE, mode="replace")
    write_memory_file(user_id, "技能标签.md", SKILL_TAGS, mode="replace")
    write_memory_file(user_id, "优化历史.md", OPTIMIZATION_HISTORY, mode="replace")
    print(f"[3/5] 记忆文件已写入: 职业偏好.md / 技能标签.md / 优化历史.md")

    # 4. 保存示例简历快照
    rid1 = save_resume_snapshot(user_id, SAMPLE_OPTIMIZED_RESUME)
    print(f"[4/5] 简历快照已保存: {rid1}")

    # 5. 保存用户配置
    user_settings = UserSettings(
        default_template="professional",
        language_style="professional",
        output_language="zh-CN",
        auto_save_resume=True,
    )
    settings_path = save_user_settings(user_id, user_settings)
    print(f"[5/5] 用户配置已保存: {settings_path}")

    print(f"\n=== 初始化完成 ===")
    print(f"数据目录: {user_dir}")
    print()
    print("接下来可以启动服务测试:")
    print("  cd ResumeHarness")
    print("  python -m backend.app")
    print()
    print("=== 对话测试建议 ===")
    print()
    print("1. 基础对话测试:")
    print('   输入: "你好，请介绍一下你自己"')
    print()
    print("2. 简历优化测试（会触发自动保存 + resume_generated 事件）:")
    print('   输入: "请根据我的简历，帮我优化一份投递字节跳动高级前端工程师岗位的简历"')
    print()
    print("3. JD 抓取测试（会调用 web_fetch 工具）:")
    print('   输入: "帮我分析这个岗位要求: https://jobs.example.com/frontend-2024"')
    print('   （注意：示例 URL 会抓取失败，这是正常的）')
    print()
    print("4. 记忆写入测试:")
    print('   输入: "我偏好用 STAR 法则写简历，请记住这个偏好"')
    print()
    print("5. 多轮对话测试:")
    print('   输入: "帮我优化简历" → "工作经历部分需要更具体的数据" → "再调整一下技能标签"')
    print()
    print("=== API 测试建议 ===")
    print()
    print("# 记忆管理")
    print("curl http://localhost:8000/api/memory")
    print("curl http://localhost:8000/api/memory/职业偏好.md")
    print()
    print("# 简历下载")
    print(f"curl http://localhost:8000/api/resume/{rid1}/download?format=pdf -o test.pdf")
    print(f"curl http://localhost:8000/api/resume/{rid1}/download?format=markdown -o test.md")
    print(f"curl http://localhost:8000/api/resume/{rid1}/preview?template=academic")
    print()
    print("# 工具/技能")
    print("curl http://localhost:8000/api/tools")
    print("curl http://localhost:8000/api/skills")
    print("curl http://localhost:8000/api/mcp/status")
    print()
    print("# 会话")
    print("curl http://localhost:8000/api/sessions")
    print()
    print("# 配置")
    print("curl http://localhost:8000/api/settings")


if __name__ == "__main__":
    seed()
