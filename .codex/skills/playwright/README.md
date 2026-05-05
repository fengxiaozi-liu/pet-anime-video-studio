# Playwright 技能

为使用 Playwright 构建完整 E2E 测试套件提供专家级协助，包括页面对象、fixture、视觉回归和 CI/CD 集成。

## 概览

此技能为 Playwright 测试提供专项指导，覆盖端到端测试、视觉回归、可访问性测试和 API 测试。它可以帮助创建可维护、可靠，并能集成到 CI/CD 流水线中的测试套件。

## 何时使用

- 为新项目设置 Playwright
- 为测试创建页面对象模型
- 实现视觉回归测试
- 为测试套件添加可访问性测试
- 配置跨浏览器测试
- 设置 CI/CD 集成

## 快速开始

### 基础设置

```json
{
  "projectType": "web",
  "framework": "react",
  "browsers": ["chromium", "firefox", "webkit"]
}
```

### 完整测试套件

```json
{
  "projectType": "web",
  "framework": "nextjs",
  "features": ["visual", "a11y", "api"],
  "ci": "github",
  "browsers": ["chromium", "firefox"],
  "baseUrl": "http://localhost:3000"
}
```

## 生成的结构

```
tests/
├── playwright.config.ts      # 配置
├── fixtures/                 # 测试 fixture
│   ├── base.ts
│   └── auth.ts
├── pages/                    # 页面对象
│   ├── BasePage.ts
│   └── LoginPage.ts
├── e2e/                      # E2E 测试
│   ├── auth/
│   └── dashboard/
├── visual/                   # 视觉测试
├── a11y/                     # 可访问性测试
└── utils/                    # 工具函数
```

## 功能

### 页面对象模型

```typescript
// tests/pages/LoginPage.ts
import { Page, Locator, expect } from '@playwright/test';

export class LoginPage {
  readonly page: Page;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.emailInput = page.getByLabel('Email');
    this.passwordInput = page.getByLabel('Password');
    this.submitButton = page.getByRole('button', { name: 'Sign in' });
  }

  async login(email: string, password: string) {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
    await this.submitButton.click();
  }
}
```

### 自定义 Fixtures

```typescript
// tests/fixtures/base.ts
import { test as base } from '@playwright/test';
import { LoginPage } from '../pages/LoginPage';

export const test = base.extend<{ loginPage: LoginPage }>({
  loginPage: async ({ page }, use) => {
    await use(new LoginPage(page));
  },
});
```

### 视觉回归

```typescript
test('homepage matches snapshot', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveScreenshot('homepage.png', {
    fullPage: true,
    animations: 'disabled',
  });
});
```

### 可访问性测试

```typescript
import AxeBuilder from '@axe-core/playwright';

test('page has no a11y violations', async ({ page }) => {
  await page.goto('/');
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
```

### API 测试

```typescript
test('API returns user data', async ({ request }) => {
  const response = await request.get('/api/users/1');
  expect(response.ok()).toBeTruthy();
  const user = await response.json();
  expect(user.name).toBeDefined();
});
```

## 测试示例

### 基础 E2E 测试

```typescript
import { test, expect } from '../fixtures/base';

test.describe('Authentication', () => {
  test('user can login', async ({ loginPage, page }) => {
    await page.goto('/login');
    await loginPage.login('user@example.com', 'password');
    await expect(page).toHaveURL('/dashboard');
  });
});
```

### 参数化测试

```typescript
const testCases = [
  { email: 'user1@test.com', expected: 'User 1' },
  { email: 'user2@test.com', expected: 'User 2' },
];

for (const { email, expected } of testCases) {
  test(`displays name for ${email}`, async ({ page }) => {
    await page.goto(`/users?email=${email}`);
    await expect(page.getByRole('heading')).toContainText(expected);
  });
}
```

### 移动端测试

```typescript
import { devices } from '@playwright/test';

test.use({ ...devices['iPhone 13'] });

test('mobile menu works', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Menu' }).click();
  await expect(page.getByRole('navigation')).toBeVisible();
});
```

## CI/CD 集成

### GitHub Actions

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npx playwright test
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
```

## 与流程集成

| 流程 | 集成方式 |
|---------|-------------|
| e2e-testing-setup | 主要测试技能 |
| visual-regression-testing | 截图对比 |
| accessibility-testing | WCAG 合规 |
| api-testing | API 端点测试 |
| ci-cd-integration | 流水线设置 |

## 配置选项

| 选项 | 默认值 | 描述 |
|--------|---------|-------------|
| browsers | all | 要测试的浏览器 |
| retries | 0 | 不稳定测试的重试次数 |
| workers | auto | 并行 worker |
| reporter | html | 报告格式 |

## 最佳实践

1. **页面对象**：封装页面交互
2. **Fixtures**：在测试之间共享设置
3. **定位器**：使用可访问选择器（role、label）
4. **断言**：使用 web-first 断言
5. **隔离性**：每个测试都应相互独立

## 参考资料

- [Playwright 文档](https://playwright.dev/)
- [页面对象模型](https://playwright.dev/docs/pom)
- [视觉回归](https://playwright.dev/docs/test-snapshots)
- [可访问性测试](https://playwright.dev/docs/accessibility-testing)
- [CI/CD 集成](https://playwright.dev/docs/ci)
